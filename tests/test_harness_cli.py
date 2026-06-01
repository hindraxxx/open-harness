import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "harness"


class HarnessCliTest(unittest.TestCase):
    def run_cli(
        self,
        cwd: Path,
        *args: str,
        check: bool = True,
        env: Optional[dict[str, str]] = None,
    ) -> subprocess.CompletedProcess:
        command_env = os.environ.copy()
        command_env.pop("LINEAR_API_KEY", None)
        command_env.pop("LINEAR_TEAM_ID", None)
        command_env.pop("LINEAR_PROJECT_ID", None)
        if env:
            command_env.update(env)
        result = subprocess.run(
            [str(CLI), *args],
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=command_env,
        )
        if check and result.returncode != 0:
            self.fail(f"command failed: {args}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def test_init_creates_project_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")

            self.assertTrue((cwd / ".harness" / "harness.yml").exists())
            self.assertTrue((cwd / ".harness" / "templates" / "session.md").exists())
            self.assertTrue((cwd / ".harness" / "agents" / "planning.md").exists())
            self.assertTrue((cwd / "AGENTS.md").exists())
            self.assertIn(".env", (cwd / ".gitignore").read_text().splitlines())

    def test_start_uses_local_session_id_and_linear_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout", "--linear", "WF-123")

            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            self.assertTrue(artifact.exists())
            self.assertTrue((artifact.parent / "proof").is_dir())
            text = artifact.read_text()
            self.assertIn('session_id: "req-login-timeout"', text)
            self.assertIn('linear_issue_key: "WF-123"', text)

    def test_invalid_transition_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")

            result = self.run_cli(cwd, "transition", "req-login-timeout", "implementation", check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid transition", result.stderr)

    def test_missing_linear_token_blocks_only_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout", "--linear", "WF-123")

            result = self.run_cli(cwd, "sync-linear", "req-login-timeout", check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing LINEAR_API_KEY", result.stderr)
            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            self.assertIn('status: "start"', artifact.read_text())

    def test_global_env_allows_linear_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp) / "project"
            cwd.mkdir()
            global_env = Path(tmp) / "global.env"
            global_env.write_text("LINEAR_API_KEY=global-token\n")
            env = {"HARNESS_GLOBAL_ENV": str(global_env)}

            self.run_cli(cwd, "init", env=env)
            self.run_cli(cwd, "start", "req-login-timeout", "--linear", "WF-123", env=env)
            result = self.run_cli(cwd, "sync-linear", "req-login-timeout", env=env)

            self.assertIn("linear sync stubbed for WF-123", result.stdout)
            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            self.assertIn('linear_sync: "stubbed:', artifact.read_text())

    def test_project_env_overrides_missing_global_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp) / "project"
            cwd.mkdir()
            global_env = Path(tmp) / "missing-global.env"
            env = {"HARNESS_GLOBAL_ENV": str(global_env)}

            self.run_cli(cwd, "init", env=env)
            (cwd / ".env").write_text("LINEAR_API_KEY=project-token\n")
            self.run_cli(cwd, "start", "req-login-timeout", "--linear", "WF-123", env=env)
            result = self.run_cli(cwd, "sync-linear", "req-login-timeout", env=env)

            self.assertIn("linear sync stubbed for WF-123", result.stdout)

    def test_attach_proof_records_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            proof = cwd / "result.txt"
            proof.write_text("ok\n")
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")
            self.run_cli(cwd, "attach-proof", "req-login-timeout", str(proof))

            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            self.assertIn("- [x] [result.txt](proof/result.txt)", artifact.read_text())
            self.assertTrue((artifact.parent / "proof" / "result.txt").exists())


if __name__ == "__main__":
    unittest.main()
