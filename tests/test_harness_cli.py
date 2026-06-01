import os
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
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

    def test_preflight_blocks_code_edits_before_implementation(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")

            result = self.run_cli(cwd, "preflight-edit", "req-login-timeout", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("product code edits blocked", result.stderr)

    def test_upgrade_guardrails_overwrites_bootstrap(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            (cwd / "AGENTS.md").write_text("old\n")

            self.run_cli(cwd, "upgrade-guardrails")

            text = (cwd / "AGENTS.md").read_text()
            self.assertIn("preflight-edit", text)
            self.assertIn("If preflight blocks", text)

    def test_missing_linear_token_blocks_only_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            env = {"HARNESS_GLOBAL_ENV": str(Path(tmp) / "missing.env")}
            self.run_cli(cwd, "init", env=env)
            self.run_cli(cwd, "start", "req-login-timeout", "--linear", "WF-123", env=env)

            result = self.run_cli(cwd, "sync-linear", "req-login-timeout", check=False, env=env)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing LINEAR_API_KEY", result.stderr)
            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            self.assertIn('status: "start"', artifact.read_text())

    def test_global_env_allows_linear_sync(self):
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers["Content-Length"])
                body = self.rfile.read(length).decode("utf-8")
                requests.append(body)
                if "query HarnessIssue" in body:
                    response = {
                        "data": {
                            "issue": {
                                "id": "issue-id",
                                "identifier": "WF-123",
                                "title": "Login Timeout",
                                "url": "https://linear.app/example/issue/WF-123/login-timeout",
                                "state": {"id": "backlog-id", "name": "Backlog"},
                                "team": {
                                    "id": "team-id",
                                    "states": {
                                        "nodes": [
                                            {"id": "backlog-id", "name": "Backlog"},
                                            {"id": "planning-id", "name": "Planning"},
                                        ]
                                    },
                                },
                            }
                        }
                    }
                else:
                    response = {
                        "data": {
                            "issueUpdate": {
                                "success": True,
                                "issue": {
                                    "id": "issue-id",
                                    "identifier": "WF-123",
                                    "state": {"id": "backlog-id", "name": "Backlog"},
                                },
                            }
                        }
                    }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(__import__("json").dumps(response).encode("utf-8"))

            def log_message(self, _format, *args):
                return

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            with tempfile.TemporaryDirectory() as tmp:
                cwd = Path(tmp) / "project"
                cwd.mkdir()
                global_env = Path(tmp) / "global.env"
                global_env.write_text("LINEAR_API_KEY=global-token\n")
                env = {
                    "HARNESS_GLOBAL_ENV": str(global_env),
                    "HARNESS_LINEAR_API_URL": f"http://127.0.0.1:{server.server_port}/graphql",
                }

                self.run_cli(cwd, "init", env=env)
                self.run_cli(cwd, "start", "req-login-timeout", "--linear", "WF-123", env=env)
                result = self.run_cli(cwd, "sync-linear", "req-login-timeout", env=env)

                self.assertIn("linear synced: WF-123 -> Backlog", result.stdout)
                artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
                self.assertIn('linear_sync: "state:Backlog:', artifact.read_text())
                self.assertEqual(len(requests), 2)
        finally:
            server.shutdown()
            server.server_close()

    def test_project_env_overrides_missing_global_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp) / "project"
            cwd.mkdir()
            global_env = Path(tmp) / "missing-global.env"
            env = {
                "HARNESS_GLOBAL_ENV": str(global_env),
                "HARNESS_LINEAR_API_URL": "http://127.0.0.1:9/graphql",
            }

            self.run_cli(cwd, "init", env=env)
            (cwd / ".env").write_text("LINEAR_API_KEY=project-token\n")
            self.run_cli(cwd, "start", "req-login-timeout", "--linear", "WF-123", env=env)
            result = self.run_cli(cwd, "sync-linear", "req-login-timeout", check=False, env=env)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Linear API request failed", result.stderr)

    def test_start_can_create_linear_issue(self):
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers["Content-Length"])
                requests.append((self.headers, self.rfile.read(length).decode("utf-8")))
                response = {
                    "data": {
                        "issueCreate": {
                            "success": True,
                            "issue": {
                                "id": "issue-id",
                                "identifier": "WF-999",
                                "title": "Login Timeout",
                                "url": "https://linear.app/example/issue/WF-999/login-timeout",
                            },
                        }
                    }
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(__import__("json").dumps(response).encode("utf-8"))

            def log_message(self, _format, *args):
                return

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            with tempfile.TemporaryDirectory() as tmp:
                cwd = Path(tmp)
                env = {
                    "HARNESS_LINEAR_API_URL": f"http://127.0.0.1:{server.server_port}/graphql",
                    "HARNESS_GLOBAL_ENV": str(Path(tmp) / "missing.env"),
                    "LINEAR_API_KEY": "test-token",
                    "LINEAR_TEAM_ID": "team-id",
                    "LINEAR_PROJECT_ID": "project-id",
                }
                self.run_cli(cwd, "init", env=env)
                result = self.run_cli(
                    cwd,
                    "start",
                    "req-login-timeout",
                    "--create-linear",
                    "--title",
                    "Login Timeout",
                    "--description",
                    "Harness session",
                    env=env,
                )

                self.assertIn("linear issue: WF-999", result.stdout)
                artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
                text = artifact.read_text()
                self.assertIn('linear_issue_key: "WF-999"', text)
                self.assertIn('linear_issue_url: "https://linear.app/example/issue/WF-999/login-timeout"', text)
                self.assertEqual(requests[0][0]["Authorization"], "test-token")
                self.assertIn('"projectId": "project-id"', requests[0][1])
        finally:
            server.shutdown()
            server.server_close()

    def test_create_linear_requires_team_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            env = {"LINEAR_API_KEY": "test-token", "HARNESS_GLOBAL_ENV": str(Path(tmp) / "missing.env")}
            self.run_cli(cwd, "init", env=env)
            result = self.run_cli(cwd, "start", "req-login-timeout", "--create-linear", check=False, env=env)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing LINEAR_TEAM_ID", result.stderr)

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
