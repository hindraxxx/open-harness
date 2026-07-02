#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


TEST_MODULE = "tests.test_harness_cli"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ESTIMATED_SECONDS = {
    f"{TEST_MODULE}.HarnessCliTest.test_update_aborts_before_pull_when_harness_source_is_dirty": 10.5,
    f"{TEST_MODULE}.HarnessCliTest.test_update_pulls_harness_source_when_behind_origin_main": 9.8,
    f"{TEST_MODULE}.HarnessCliTest.test_install_script_clones_and_symlinks_harness": 5.4,
    f"{TEST_MODULE}.HarnessCliTest.test_modified_gitignore_does_not_count_as_product_change": 4.3,
}
DEFAULT_ESTIMATED_SECONDS = 0.25


def load_test_ids() -> list[str]:
    suite = unittest.defaultTestLoader.loadTestsFromName(TEST_MODULE)
    ids: list[str] = []

    def walk(item: unittest.TestSuite | unittest.TestCase) -> None:
        if isinstance(item, unittest.TestSuite):
            for child in item:
                walk(child)
        else:
            ids.append(item.id())

    walk(suite)
    return ids


def shard_tests(test_ids: list[str], workers: int) -> list[list[str]]:
    shards = [[] for _ in range(workers)]
    shard_costs = [0.0 for _ in range(workers)]
    ordered = sorted(
        test_ids,
        key=lambda test_id: ESTIMATED_SECONDS.get(test_id, DEFAULT_ESTIMATED_SECONDS),
        reverse=True,
    )
    for test_id in ordered:
        index = min(range(workers), key=lambda shard_index: shard_costs[shard_index])
        shards[index].append(test_id)
        shard_costs[index] += ESTIMATED_SECONDS.get(test_id, DEFAULT_ESTIMATED_SECONDS)
    return [shard for shard in shards if shard]


def run_shard(index: int, test_ids: list[str]) -> tuple[int, int, float, int, str, str]:
    start = time.perf_counter()
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "-q", *test_ids],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    duration = time.perf_counter() - start
    return index, len(test_ids), duration, result.returncode, result.stdout, result.stderr


def main() -> int:
    parser = argparse.ArgumentParser(description="Run harness CLI unittest shards in parallel.")
    parser.add_argument(
        "-j",
        "--workers",
        type=int,
        default=min(6, os.cpu_count() or 1),
        help="number of parallel unittest worker processes",
    )
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be >= 1")

    test_ids = load_test_ids()
    shards = shard_tests(test_ids, min(args.workers, len(test_ids)))
    started = time.perf_counter()
    failures: list[tuple[int, str, str]] = []
    results: list[tuple[int, int, float, int]] = []

    with ThreadPoolExecutor(max_workers=len(shards)) as executor:
        futures = {
            executor.submit(run_shard, index + 1, shard): index + 1
            for index, shard in enumerate(shards)
        }
        for future in as_completed(futures):
            index, count, duration, returncode, stdout, stderr = future.result()
            results.append((index, count, duration, returncode))
            if returncode != 0:
                failures.append((index, stdout, stderr))

    total = time.perf_counter() - started
    for index, count, duration, returncode in sorted(results):
        status = "ok" if returncode == 0 else "failed"
        print(f"shard {index}: {count} tests, {duration:.3f}s, {status}")
    print(f"total: {len(test_ids)} tests across {len(shards)} shards in {total:.3f}s")

    for index, stdout, stderr in failures:
        print(f"\n=== shard {index} stdout ===")
        print(stdout, end="")
        print(f"\n=== shard {index} stderr ===", file=sys.stderr)
        print(stderr, end="", file=sys.stderr)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
