# Workflow Project Agent Instructions

This repository owns the local `harness` CLI. Treat changes here as harness
release changes, not target-project guardrail edits.

## Required Checks

- After any code, test, documentation, or guardrail change in this repository,
  run the harness CLI unit suite before reporting completion:
  `rtk python3 tests/run_harness_cli_parallel.py`
- If the parallel runner is unavailable or suspect, run the canonical unittest
  command instead:
  `rtk python3 -m unittest tests/test_harness_cli.py -q`
- Report the command and result in the final response.

## Versioning

- Bump `HARNESS_VERSION` in `bin/harness` on every repository change.
- Use the existing date-based version format: `YYYY.MM.DD.N`.
- Increment the final numeric component for multiple changes on the same date.
- Keep tests that assert version behavior aligned with the version constant.

## Bootstrap Files

- `CLAUDE.md` must be a symlink to `AGENTS.md`.
- If `CLAUDE.md` does not exist, create it with:
  `rtk ln -s AGENTS.md CLAUDE.md`
- If `CLAUDE.md` exists but is not a symlink to `AGENTS.md`, stop and report the
  mismatch before changing it.

## Change Discipline

- Keep harness behavior changes surgical and covered by
  `tests/test_harness_cli.py`.
- Prefer adding or updating focused tests before changing `bin/harness`.
- Do not bypass harness state guards by editing generated artifact status
  directly in target repositories.
- Do not write `.env` secrets into artifacts, logs, comments, or proof files.

## Compatibility

- Preserve compatibility with existing target repos where practical.
- When changing canonical identifiers, paths, or generated guardrails, update
  compatibility tests and migration behavior together.

## Shell

- Prefix shell commands with `rtk`.
