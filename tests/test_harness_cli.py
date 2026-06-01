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

    def test_planning_to_implementation_requires_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")
            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            text = artifact.read_text()
            text = text.replace("- [ ] TBD", "- [ ] Build download flow", 3)
            text = text.replace("TBD", "Download Neraca as Excel", 1)
            text = text.replace("TBD", "Given user exports Neraca, file downloads successfully", 1)
            text = text.replace("TBD", "Run controller unit test", 1)
            artifact.write_text(text)

            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            blocked = self.run_cli(cwd, "transition", "req-login-timeout", "implementation", check=False)

            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("Planning must be human-approved", blocked.stdout)

            self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem")
            allowed = self.run_cli(cwd, "transition", "req-login-timeout", "implementation")

            self.assertIn("transitioned: planning -> implementation", allowed.stdout)
            self.assertIn('planning_approved: "true"', artifact.read_text())
            self.assertIn('planning_approved_hash: "', artifact.read_text())

    def test_planning_status_reports_missing_planning_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")
            self.run_cli(cwd, "transition", "req-login-timeout", "planning")

            result = self.run_cli(cwd, "validate", "req-login-timeout", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Requirement Summary must be filled", result.stdout)
            self.assertIn("Acceptance Criteria must be filled", result.stdout)
            self.assertIn("Validation Plan must be filled", result.stdout)
            self.assertIn("Implementation Checklist must be filled", result.stdout)

    def test_approve_planning_blocks_when_artifact_not_filled(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")
            self.run_cli(cwd, "transition", "req-login-timeout", "planning")

            result = self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("planning approval blocked", result.stdout)
            self.assertIn("Implementation Checklist must be filled", result.stdout)

    def test_planning_changes_after_approval_block_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")
            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            text = artifact.read_text()
            text = text.replace("TBD", "Download Neraca as Excel", 1)
            text = text.replace("- [ ] TBD", "- [ ] Acceptance exists", 1)
            text = text.replace("- [ ] TBD", "- [ ] Validation exists", 1)
            text = text.replace("- [ ] TBD", "- [x] Implementation complete", 1)
            artifact.write_text(text)

            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem")
            self.run_cli(cwd, "transition", "req-login-timeout", "implementation")
            artifact.write_text(artifact.read_text().replace("- [ ] Acceptance exists", "- [ ] Acceptance changed"))

            blocked = self.run_cli(cwd, "preflight-edit", "req-login-timeout", check=False)

            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("Planning sections changed after approval", blocked.stdout)

    def test_implementation_status_reports_unchecked_checklist_with_product_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")
            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            text = artifact.read_text()
            text = text.replace("TBD", "Download Neraca as Excel", 1)
            text = text.replace("- [ ] TBD", "- [ ] Acceptance exists", 1)
            text = text.replace("- [ ] TBD", "- [ ] Validation exists", 1)
            text = text.replace("- [ ] TBD", "- [ ] Implementation task", 1)
            artifact.write_text(text)

            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem")
            self.run_cli(cwd, "transition", "req-login-timeout", "implementation")
            (cwd / "app.py").write_text("changed\n")
            result = self.run_cli(cwd, "validate", "req-login-timeout", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Implementation Checklist has unchecked items while product changes exist", result.stdout)

    def test_review_transition_requires_full_implementation_checklist(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")
            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            text = artifact.read_text()
            text = text.replace("TBD", "Download Neraca as Excel", 1)
            text = text.replace("- [ ] TBD", "- [ ] Acceptance exists", 1)
            text = text.replace("- [ ] TBD", "- [ ] Validation exists", 1)
            text = text.replace("- [ ] TBD", "- [x] Done task\n- [ ] Undone task", 1)
            artifact.write_text(text)

            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem")
            self.run_cli(cwd, "transition", "req-login-timeout", "implementation")
            result = self.run_cli(cwd, "transition", "req-login-timeout", "review", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Implementation Checklist must be fully checked before review", result.stdout)

    def test_implementation_reports_quality_evidence_recorded_too_early(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")
            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            text = artifact.read_text()
            text = text.replace("TBD", "Download Neraca as Excel", 1)
            text = text.replace("- [ ] TBD", "- [ ] Acceptance exists", 1)
            text = text.replace("- [ ] TBD", "- [ ] Validation exists", 1)
            text = text.replace("- [ ] TBD", "- [x] Implementation task", 1)
            artifact.write_text(text)

            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem")
            self.run_cli(cwd, "transition", "req-login-timeout", "implementation")
            artifact.write_text(artifact.read_text().replace("### Commands Run\n\nTBD", "### Commands Run\n\n- premature validation"))
            result = self.run_cli(cwd, "validate", "req-login-timeout", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Quality Check evidence exists before quality-check state", result.stdout)

    def test_review_to_quality_check_requires_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")
            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            text = artifact.read_text()
            text = text.replace("TBD", "Download Neraca as Excel", 1)
            text = text.replace("- [ ] TBD", "- [ ] Acceptance exists", 1)
            text = text.replace("- [ ] TBD", "- [ ] Validation exists", 1)
            text = text.replace("- [ ] TBD", "- [x] Implementation complete", 1)
            artifact.write_text(text)

            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem")
            self.run_cli(cwd, "transition", "req-login-timeout", "implementation")
            self.run_cli(cwd, "transition", "req-login-timeout", "review")

            text = artifact.read_text()
            text = text.replace("### AI Review\n\nTBD", "### AI Review\n\nNo blocking issues.")
            text = text.replace("### Human Review\n\nTBD", "### Human Review\n\nLooks correct.")
            artifact.write_text(text)

            blocked = self.run_cli(cwd, "transition", "req-login-timeout", "quality-check", check=False)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("Human review must be approved", blocked.stdout)

            self.run_cli(cwd, "approve-review", "req-login-timeout", "--by", "Liem")
            allowed = self.run_cli(cwd, "transition", "req-login-timeout", "quality-check")

            self.assertIn("transitioned: review -> quality-check", allowed.stdout)
            self.assertIn('review_approved: "true"', artifact.read_text())

    def test_quality_check_reports_unexecuted_validation_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")
            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            text = artifact.read_text()
            text = text.replace("TBD", "Download Neraca as Excel", 1)
            text = text.replace("- [ ] TBD", "- [ ] Acceptance exists", 1)
            text = text.replace("- [ ] TBD", "- [ ] Run build", 1)
            text = text.replace("- [ ] TBD", "- [x] Implementation complete", 1)
            artifact.write_text(text)

            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem")
            self.run_cli(cwd, "transition", "req-login-timeout", "implementation")
            self.run_cli(cwd, "transition", "req-login-timeout", "review")
            text = artifact.read_text()
            text = text.replace("### AI Review\n\nTBD", "### AI Review\n\nNo blocking issues.")
            text = text.replace("### Human Review\n\nTBD", "### Human Review\n\nLooks correct.")
            artifact.write_text(text)
            self.run_cli(cwd, "approve-review", "req-login-timeout", "--by", "Liem")
            self.run_cli(cwd, "transition", "req-login-timeout", "quality-check")

            result = self.run_cli(cwd, "validate", "req-login-timeout", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Validation Plan checklist must be executed", result.stdout)
            self.assertIn("Quality Check Commands Run", result.stdout)

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

    def test_transition_auto_syncs_linear(self):
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
                                    "state": {"id": "planning-id", "name": "Planning"},
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
                }
                self.run_cli(cwd, "init", env=env)
                result = self.run_cli(cwd, "start", "req-login-timeout", "--linear", "WF-123", env=env)
                self.assertIn("linear issue: WF-123", result.stdout)
                transition = self.run_cli(cwd, "transition", "req-login-timeout", "planning", env=env)

                self.assertIn("transitioned: start -> planning", transition.stdout)
                artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
                self.assertIn('linear_sync: "state:Planning:', artifact.read_text())
                self.assertEqual(len(requests), 2)
        finally:
            server.shutdown()
            server.server_close()

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

    def test_attach_proof_records_link_under_quality_check_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            proof = cwd / "result.pdf"
            proof.write_text("%PDF\n")
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")
            self.run_cli(cwd, "attach-proof", "req-login-timeout", str(proof))

            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            text = artifact.read_text()
            quality = text.split("## Quality Check", 1)[1]
            proof_section = quality.split("### Proof", 1)[1].split("### Manual Validation", 1)[0]

            self.assertIn("- [x] [result.pdf](proof/result.pdf)", proof_section)
            self.assertNotIn("### Attached Proof", text)

    def test_done_requires_resolving_proof_file_under_proof_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")
            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            text = artifact.read_text()
            text = text.replace("TBD", "Download Neraca as Excel", 1)
            text = text.replace("- [ ] TBD", "- [x] Acceptance exists", 1)
            text = text.replace("- [ ] TBD", "- [x] Run build", 1)
            text = text.replace("- [ ] TBD", "- [x] Implementation complete", 1)
            text = text.replace("### AI Review\n\nTBD", "### AI Review\n\nNo blocking issues.")
            text = text.replace("### Human Review\n\nTBD", "### Human Review\n\nLooks correct.")
            text = text.replace("## Final Approval\n\nTBD", "## Final Approval\n\nApproved.")
            artifact.write_text(text)

            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem")
            self.run_cli(cwd, "transition", "req-login-timeout", "implementation")
            self.run_cli(cwd, "transition", "req-login-timeout", "review")
            self.run_cli(cwd, "approve-review", "req-login-timeout", "--by", "Liem")
            self.run_cli(cwd, "transition", "req-login-timeout", "quality-check")
            text = artifact.read_text()
            text = text.replace("### Commands Run\n\nTBD", "### Commands Run\n\n- build ok")
            text = text.replace("### Proof\n\n- [ ] TBD", "### Proof\n\n- [x] [missing.pdf](proof/missing.pdf)")
            artifact.write_text(text)
            result = self.run_cli(cwd, "transition", "req-login-timeout", "done", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Quality Check Proof needs at least one checked proof file under proof/", result.stdout)


if __name__ == "__main__":
    unittest.main()
