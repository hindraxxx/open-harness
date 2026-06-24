import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import json
import importlib.machinery
import importlib.util
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "harness"


class HarnessCliTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        loader = importlib.machinery.SourceFileLoader("harness_mod", str(CLI))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        cls.harness_module = module

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
        command_env["HARNESS_SKIP_LANGUAGE_SKILLS"] = "1"
        if env:
            command_env.update(env)
        old_cwd = Path.cwd()
        old_argv = sys.argv
        old_env = os.environ.copy()
        stdout = StringIO()
        stderr = StringIO()
        returncode = 0
        try:
            os.chdir(cwd)
            os.environ.clear()
            os.environ.update(command_env)
            sys.argv = [str(CLI), *args]
            with redirect_stdout(stdout), redirect_stderr(stderr):
                try:
                    self.harness_module.main()
                except SystemExit as exc:
                    returncode = exc.code if isinstance(exc.code, int) else 1
        finally:
            sys.argv = old_argv
            os.environ.clear()
            os.environ.update(old_env)
            os.chdir(old_cwd)
        result = subprocess.CompletedProcess(
            [str(CLI), *args],
            returncode,
            stdout.getvalue(),
            stderr.getvalue(),
        )
        if check and result.returncode != 0:
            self.fail(f"command failed: {args}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def run_temp_cli(
        self,
        cli: Path,
        cwd: Path,
        *args: str,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        command_env = os.environ.copy()
        command_env["HARNESS_SKIP_LANGUAGE_SKILLS"] = "1"
        result = subprocess.run(
            [str(cli), *args],
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=command_env,
        )
        if check and result.returncode != 0:
            self.fail(f"command failed: {args}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def git(self, cwd: Path, *args: str) -> subprocess.CompletedProcess:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            self.fail(f"git failed: {args}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def make_harness_git_fixture(self, tmp: Path) -> tuple[Path, Path]:
        seed = tmp / "seed"
        origin = tmp / "origin.git"
        source = tmp / "source"
        seed.mkdir()
        (seed / "bin").mkdir()
        shutil.copy2(CLI, seed / "bin" / "harness")
        os.chmod(seed / "bin" / "harness", 0o755)
        (seed / "README.md").write_text("v1\n")
        self.git(seed, "init", "-b", "main")
        self.git(seed, "config", "user.email", "test@example.com")
        self.git(seed, "config", "user.name", "Harness Test")
        self.git(seed, "add", ".")
        self.git(seed, "commit", "-m", "initial")
        self.git(seed, "clone", "--bare", str(seed), str(origin))
        self.git(tmp, "clone", str(origin), str(source))
        self.git(source, "checkout", "main")
        self.git(seed, "remote", "add", "origin", str(origin))
        (seed / "README.md").write_text("v2\n")
        self.git(seed, "add", "README.md")
        self.git(seed, "commit", "-m", "advance")
        self.git(seed, "push", "origin", "main")
        return source, source / "bin" / "harness"

    def guidance_placeholder(self) -> str:
        return (
            "## Implementation Guidance\n\nTBD\n\n"
            "### Old Flow\n\n"
            "```mermaid\n"
            "sequenceDiagram\n"
            "    participant Client\n"
            "    participant Old_Controller\n"
            "    participant Old_Service\n"
            "    participant Old_RepositoryOrGateway\n"
            "    Client->>Old_Controller: request\n"
            "    Old_Controller->>Old_Service: command/query\n"
            "    Old_Service->>Old_RepositoryOrGateway: persistence or external call\n"
            "    Old_RepositoryOrGateway-->>Old_Service: result\n"
            "    Old_Service-->>Old_Controller: response model\n"
            "    Old_Controller-->>Client: response\n"
            "```\n\n"
            "### New Flow\n\n"
            "```mermaid\n"
            "sequenceDiagram\n"
            "    participant Client\n"
            "    participant FileA_Controller\n"
            "    participant FileB_Service\n"
            "    participant FileC_RepositoryOrGateway\n"
            "    Client->>FileA_Controller: request\n"
            "    FileA_Controller->>FileB_Service: command/query\n"
            "    alt scoped change\n"
            "        FileB_Service->>FileB_Service: apply scoped behavior change\n"
            "    else existing behavior preserved\n"
            "        FileB_Service->>FileB_Service: preserve existing behavior\n"
            "    end\n"
            "    FileB_Service->>FileC_RepositoryOrGateway: persistence or external call\n"
            "    FileC_RepositoryOrGateway-->>FileB_Service: result\n"
            "    FileB_Service-->>FileA_Controller: response model\n"
            "    FileA_Controller-->>Client: response\n"
            "```\n\n"
            "### Implementation Sketch\n\nTBD\n\n"
            "### Code Anchors\n\nTBD"
        )

    def with_guidance(self, text: str) -> str:
        guidance = "\n".join(
            [
                "Expected location: inspect the module named by the requirement before editing.",
                "Invariants: do not change unrelated routes, validation, persistence, or views unless verification proves they depend on the change.",
                "",
                "### Old Flow",
                "",
                "```mermaid",
                "sequenceDiagram",
                "    participant Client",
                "    participant ReportController_php",
                "    participant ReportService",
                "    participant ReportRepository",
                "    Client->>ReportController_php: request",
                "    ReportController_php->>ReportService: command/query",
                "    ReportService->>ReportRepository: persistence or external call",
                "    ReportRepository-->>ReportService: result",
                "    ReportService-->>ReportController_php: response model",
                "    ReportController_php-->>Client: response",
                "```",
                "",
                "### New Flow",
                "",
                "```mermaid",
                "sequenceDiagram",
                "    participant Client",
                "    participant ReportController_php",
                "    participant ReportService",
                "    participant ReportRepository",
                "    Client->>ReportController_php: request",
                "    ReportController_php->>ReportService: command/query",
                "    alt scoped behavior applies",
                "        ReportService->>ReportService: apply scoped behavior change",
                "    else existing behavior",
                "        ReportService->>ReportService: preserve existing behavior",
                "    end",
                "    ReportService->>ReportRepository: persistence or external call",
                "    ReportRepository-->>ReportService: result",
                "    ReportService-->>ReportController_php: response model",
                "    ReportController_php-->>Client: response",
                "```",
                "",
                "### Implementation Sketch",
                "",
                "Pseudocode: preserve existing successful flow and apply the scoped behavior change only.",
                "",
                "### Code Anchors",
                "",
                "- Use the existing module and branch conditions verified during planning.",
            ]
        )
        return text.replace(self.guidance_placeholder(), f"## Implementation Guidance\n\n{guidance}", 1)

    def enter_quality_check(self, cwd: Path, validation_item: str = "Run validation") -> Path:
        self.run_cli(cwd, "init")
        self.run_cli(cwd, "start", "req-login-timeout")
        artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
        text = artifact.read_text()
        text = text.replace("TBD", "Download Neraca as Excel", 1)
        text = text.replace("- [ ] TBD", "- [x] Acceptance exists", 1)
        text = text.replace("- [ ] TBD", f"- [x] {validation_item}", 1)
        text = text.replace("- [ ] TBD", "- [x] Implementation complete", 1)
        text = text.replace("### AI Review\n\nTBD", "### AI Review\n\nNo blocking issues.")
        text = text.replace("### Human Review\n\nTBD", "### Human Review\n\nLooks correct.")
        artifact.write_text(self.with_guidance(text))
        self.run_cli(cwd, "transition", "req-login-timeout", "planning")
        self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem")
        self.run_cli(cwd, "transition", "req-login-timeout", "implementation")
        self.run_cli(cwd, "transition", "req-login-timeout", "review")
        self.run_cli(cwd, "approve-review", "req-login-timeout", "--by", "Liem")
        self.run_cli(cwd, "transition", "req-login-timeout", "quality-check")
        return artifact

    def complete_quality_check(self, cwd: Path, artifact: Path) -> None:
        proof = cwd / "screenshot.png"
        proof.write_text("png\n")
        self.run_cli(cwd, "attach-proof", "req-login-timeout", str(proof))
        text = artifact.read_text()
        text = text.replace(
            "### Commands Run\n\nTBD",
            "### Commands Run\n\n- curl -i http://localhost/api/neraca\n- Sample response: status 200",
        )
        text = text.replace("### Manual Validation\n\nTBD", "### Manual Validation\n\nView validated in browser.")
        artifact.write_text(self.with_guidance(text))

    def enter_review(self, cwd: Path) -> Path:
        self.run_cli(cwd, "init")
        self.run_cli(cwd, "start", "req-login-timeout")
        artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
        text = artifact.read_text()
        text = text.replace("TBD", "Download Neraca as Excel", 1)
        text = text.replace("- [ ] TBD", "- [x] Acceptance exists", 1)
        text = text.replace("- [ ] TBD", "- [x] Run validation", 1)
        text = text.replace("- [ ] TBD", "- [x] Implementation complete", 1)
        artifact.write_text(self.with_guidance(text))
        self.run_cli(cwd, "transition", "req-login-timeout", "planning")
        self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem")
        self.run_cli(cwd, "transition", "req-login-timeout", "implementation")
        self.run_cli(cwd, "transition", "req-login-timeout", "review")
        return artifact

    def test_init_creates_project_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            result = self.run_cli(cwd, "init")

            self.assertTrue((cwd / ".harness" / "harness.yml").exists())
            self.assertTrue((cwd / ".harness" / "harness.db").exists())
            self.assertTrue((cwd / ".harness" / "templates" / "session.md").exists())
            self.assertTrue((cwd / ".harness" / "agents" / "planning.md").exists())
            self.assertTrue((cwd / ".harness" / "project" / "index.md").exists())
            self.assertTrue((cwd / "AGENTS.md").exists())
            self.assertIn("Split Session Requests", (cwd / ".harness" / "agents" / "common.md").read_text())
            self.assertIn("child-session planning", (cwd / "AGENTS.md").read_text())
            self.assertIn(".env", (cwd / ".gitignore").read_text().splitlines())
            self.assertEqual(self.harness_module.HARNESS_VERSION, (cwd / ".harness" / "version").read_text().strip())
            self.assertIn(f"harness version: none -> {self.harness_module.HARNESS_VERSION}", result.stdout)

    def test_start_uses_local_session_id_and_sqlite_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")

            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            html_artifact = artifact.with_suffix(".html")
            self.assertTrue(artifact.exists())
            self.assertTrue(html_artifact.exists())
            self.assertTrue((artifact.parent / "proof").is_dir())
            text = artifact.read_text()
            self.assertIn('session_id: "req-login-timeout"', text)
            self.assertIn("## Implementation Guidance", text)
            self.assertNotIn("linear_issue_key", text)
            html_text = html_artifact.read_text()
            self.assertIn("Harness Artifact: req-login-timeout", html_text)
            self.assertIn("<h2>Implementation Guidance</h2>", html_text)
            self.assertIn('<div class="mermaid">sequenceDiagram', html_text)
            self.assertIn("cdn.jsdelivr.net/npm/mermaid", html_text)
            with sqlite3.connect(cwd / ".harness" / "harness.db") as conn:
                row = conn.execute("SELECT state FROM sessions WHERE session_id = ?", ("req-login-timeout",)).fetchone()
            self.assertEqual(("start",), row)

    def test_plan_epic_splits_three_stories_into_child_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")

            result = self.run_cli(
                cwd,
                "plan-epic",
                "epic-approval",
                "--story",
                "story-001:Maker submits request",
                "--story",
                "story-002:Checker reviews request",
                "--story",
                "story-003:Audit trail",
            )

            epic = cwd / ".harness" / "sessions" / "epic-approval"
            self.assertIn("mode: child-session", result.stdout)
            self.assertTrue((epic / "epic-plan.md").exists())
            self.assertTrue((epic / "synthesis.md").exists())
            index_html = epic / "index.html"
            self.assertTrue(index_html.exists())
            self.assertIn("children/story-001/plan.html", index_html.read_text())
            story_plan = epic / "children" / "story-001" / "plan.md"
            story_html = epic / "children" / "story-001" / "plan.html"
            metadata_path = epic / "children" / "story-001" / "metadata.json"
            self.assertTrue(story_plan.exists())
            self.assertTrue(story_html.exists())
            story_plan_text = story_plan.read_text()
            self.assertIn('session_id: "story-001"', story_plan_text)
            self.assertIn('planning_approved: "false"', story_plan_text)
            self.assertIn('parent_session_id: "epic-approval"', story_plan_text)
            story_html_text = story_html.read_text()
            self.assertIn("Session Metadata", story_html_text)
            self.assertIn("State: draft", story_html_text)
            self.assertIn("GMT+7", story_html_text)
            self.assertNotIn("<p>---</p>", story_html_text)
            metadata = json.loads(metadata_path.read_text())
            self.assertEqual("story-001", metadata["session_id"])
            self.assertEqual("epic-approval", metadata["epic_id"])
            self.assertEqual("story-001", metadata["story_id"])
            self.assertEqual("Maker submits request", metadata["title"])
            self.assertEqual("", metadata["planning_session_id"])
            self.assertEqual("children/story-001/plan.md", metadata["plan_md"])
            self.assertEqual("children/story-001/plan.html", metadata["plan_html"])
            self.assertEqual("draft", metadata["status"])
            self.assertEqual([], metadata["dependencies"])
            self.assertEqual(1, metadata["implementation_order"])

    def test_plan_epic_defaults_two_stories_to_single_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")

            result = self.run_cli(
                cwd,
                "plan-epic",
                "epic-small",
                "--story",
                "story-001:First behavior",
                "--story",
                "story-002:Second behavior",
            )

            epic = cwd / ".harness" / "sessions" / "epic-small"
            self.assertIn("mode: single-session", result.stdout)
            self.assertTrue((epic / "index.html").exists())
            self.assertFalse((epic / "children" / "story-001" / "metadata.json").exists())

    def test_plan_epic_split_override_creates_child_artifacts_for_two_stories(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")

            result = self.run_cli(
                cwd,
                "plan-epic",
                "epic-two-large",
                "--split-stories",
                "--story",
                "story-001:Large backend behavior",
                "--story",
                "story-002:Large frontend behavior",
            )

            epic = cwd / ".harness" / "sessions" / "epic-two-large"
            self.assertIn("mode: child-session", result.stdout)
            self.assertTrue((epic / "children" / "story-001" / "plan.html").exists())
            self.assertTrue((epic / "children" / "story-002" / "metadata.json").exists())

    def test_split_session_creates_child_artifacts_during_planning(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "epic-approval")
            self.run_cli(cwd, "transition", "epic-approval", "planning")

            result = self.run_cli(
                cwd,
                "split-session",
                "epic-approval",
                "--story",
                "story-001:Maker submits request",
                "--story",
                "story-002:Checker reviews request",
            )

            epic = cwd / ".harness" / "sessions" / "epic-approval"
            self.assertIn("split session: epic-approval", result.stdout)
            self.assertIn("parent artifact:", result.stdout)
            self.assertTrue((epic / "artifact.md").exists())
            self.assertTrue((epic / "artifact.html").exists())
            self.assertTrue((epic / "index.html").exists())
            self.assertTrue((epic / "epic-plan.md").exists())
            self.assertTrue((epic / "synthesis.md").exists())
            self.assertTrue((epic / "children" / "story-001" / "plan.md").exists())
            self.assertTrue((epic / "children" / "story-001" / "plan.html").exists())
            metadata = json.loads((epic / "children" / "story-001" / "metadata.json").read_text())
            self.assertEqual("epic-approval", metadata["epic_id"])
            self.assertEqual("story-001", metadata["story_id"])
            self.assertEqual("children/story-001/plan.md", metadata["plan_md"])
            with sqlite3.connect(cwd / ".harness" / "harness.db") as conn:
                row = conn.execute("SELECT state FROM sessions WHERE session_id = ?", ("epic-approval",)).fetchone()
            self.assertEqual(("planning",), row)

    def test_split_session_requires_planning_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "epic-approval")

            result = self.run_cli(
                cwd,
                "split-session",
                "epic-approval",
                "--story",
                "story-001:Maker submits request",
                check=False,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("split-session requires session state 'planning', current state is 'start'", result.stderr)

    def test_implement_resolves_ready_story_from_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(
                cwd,
                "plan-epic",
                "epic-approval",
                "--split-stories",
                "--story",
                "story-001:Maker submits request",
            )
            metadata_path = cwd / ".harness" / "sessions" / "epic-approval" / "children" / "story-001" / "metadata.json"
            metadata = json.loads(metadata_path.read_text())
            metadata["status"] = "ready"
            metadata["planning_session_id"] = "child-session-id-a"
            metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")

            result = self.run_cli(cwd, "implement", "story-001")

            self.assertIn("implementation target: story-001", result.stdout)
            self.assertIn("epic: epic-approval", result.stdout)
            self.assertIn("status: ready", result.stdout)
            self.assertIn("planning_session_id: child-session-id-a", result.stdout)
            self.assertIn(".harness/sessions/epic-approval/children/story-001/plan.md", result.stdout)

    def test_implement_blocks_missing_and_not_ready_stories(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            missing = self.run_cli(cwd, "implement", "story-404", check=False)
            self.assertNotEqual(0, missing.returncode)
            self.assertIn("story not found: story-404", missing.stderr)

            self.run_cli(
                cwd,
                "plan-epic",
                "epic-approval",
                "--split-stories",
                "--story",
                "story-001:Maker submits request",
            )
            blocked = self.run_cli(cwd, "implement", "story-001", check=False)
            self.assertNotEqual(0, blocked.returncode)
            self.assertIn("story story-001 is not ready for implementation: status=draft", blocked.stderr)

    def test_implement_blocks_until_dependencies_are_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(
                cwd,
                "plan-epic",
                "epic-approval",
                "--split-stories",
                "--story",
                "story-001:Maker submits request",
                "--story",
                "story-002:Checker reviews request",
            )
            story_1_metadata = cwd / ".harness" / "sessions" / "epic-approval" / "children" / "story-001" / "metadata.json"
            story_1 = json.loads(story_1_metadata.read_text())
            story_1["status"] = "ready"
            story_1_metadata.write_text(json.dumps(story_1, indent=2, sort_keys=True) + "\n")
            story_2_metadata = cwd / ".harness" / "sessions" / "epic-approval" / "children" / "story-002" / "metadata.json"
            story_2 = json.loads(story_2_metadata.read_text())
            story_2["status"] = "ready"
            story_2["dependencies"] = ["story-001"]
            story_2_metadata.write_text(json.dumps(story_2, indent=2, sort_keys=True) + "\n")

            result = self.run_cli(cwd, "implement", "story-002", check=False)

            self.assertNotEqual(0, result.returncode)
            self.assertIn("implementation blocked", result.stdout)
            self.assertIn("- dependency story-001: status=ready", result.stdout)

    def test_status_refreshes_html_from_current_markdown_and_escapes_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")
            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            html_artifact = artifact.with_suffix(".html")
            metadata, body = self.harness_module.parse_frontmatter(artifact.read_text())
            metadata["created_at"] = "2026-06-24T11:30:16+00:00"
            metadata["updated_at"] = "2026-06-24T11:41:43+00:00"
            artifact.write_text(
                self.harness_module.dump_frontmatter(metadata, body).replace(
                    "## Requirement Summary\n\nTBD",
                    "\n".join(
                        [
                            "## Requirement Summary",
                            "",
                            "Review <script>alert('x')</script> safely.",
                            "- **Primary target**: `src/main/kotlin/ProfileServiceV2.kt:250-330`",
                            "- **`MabSubmitCreditApplicationRequest.java` (web layer) — add field:**",
                            "- Literal code keeps markers: `**not bold**`",
                            "",
                            "1. In `web/src/UserController.java`, add `requestId`.",
                            "2. In `UserConsentService.java`, pass `requestId` through.",
                            "",
                            "| RFC Ref | Task | SP | PIC |",
                            "| --- | --- | --- | --- |",
                            "| 1.1 / 1.1.1 | Assign users to treatment group | 1 | Rizal Ferdian |",
                            "",
                            "```python",
                            "print('<safe>')",
                            "```",
                            "",
                            "```mermaid",
                            "sequenceDiagram",
                            "    participant Client",
                            "    participant ReportService",
                            "    Client->>ReportService: render diagram",
                            "```",
                            "",
                            "~~~python",
                            "print('tilde')",
                            "~~~",
                            "",
                            "~~~mermaid",
                            "sequenceDiagram",
                            "    participant Client",
                            "    participant TildeService",
                            "    Client->>TildeService: render tilde diagram",
                            "~~~",
                        ]
                    ),
                    1,
                )
            )

            result = self.run_cli(cwd, "status", "req-login-timeout")

            self.assertIn(f"HTML artifact: {html_artifact.resolve()}", result.stdout)
            html_text = html_artifact.read_text()
            self.assertIn("Wednesday, 24 June 2026 18:30:16 GMT+7", html_text)
            self.assertIn("Wednesday, 24 June 2026 18:41:43 GMT+7", html_text)
            self.assertNotIn("2026-06-24T11:30:16+00:00", html_text)
            self.assertIn("Review &lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt; safely.", html_text)
            self.assertNotIn("<script>alert", html_text)
            self.assertIn("<li><strong>Primary target</strong>: <code>src/main/kotlin/ProfileServiceV2.kt:250-330</code></li>", html_text)
            self.assertIn("<li><strong><code>MabSubmitCreditApplicationRequest.java</code> (web layer) — add field:</strong></li>", html_text)
            self.assertIn("<li>Literal code keeps markers: <code>**not bold**</code></li>", html_text)
            self.assertIn("<ol><li>In <code>web/src/UserController.java</code>, add <code>requestId</code>.</li>", html_text)
            self.assertIn("<li>In <code>UserConsentService.java</code>, pass <code>requestId</code> through.</li></ol>", html_text)
            self.assertIn("width: min(1380px, calc(100% - 40px));", html_text)
            self.assertIn("grid-template-columns: minmax(0, 1fr) minmax(280px, 340px);", html_text)
            self.assertIn("overflow-wrap: break-word;", html_text)
            self.assertIn("overflow-wrap: anywhere;", html_text)
            self.assertIn(".meta th { width: 34%; }", html_text)
            self.assertIn("<td>Rizal Ferdian</td>", html_text)
            self.assertIn(".meta, .meta tbody, .meta tr, .meta th, .meta td { display: block; width: 100%; }", html_text)
            self.assertIn('<code class="language-python">print(&#x27;&lt;safe&gt;&#x27;)</code>', html_text)
            self.assertIn('<code class="language-python">print(&#x27;tilde&#x27;)</code>', html_text)
            self.assertIn('<div class="mermaid">sequenceDiagram', html_text)
            self.assertIn("Client-&gt;&gt;ReportService: render diagram", html_text)
            self.assertIn("Client-&gt;&gt;TildeService: render tilde diagram", html_text)
            self.assertIn('<button type="button" class="diagram-open">Open diagram</button>', html_text)
            self.assertIn('<dialog class="diagram-modal" id="diagram-modal">', html_text)
            self.assertIn('modalBody.replaceChildren(diagram.cloneNode(true));', html_text)
            self.assertIn("mermaid.initialize", html_text)

    def test_list_reports_no_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")

            result = self.run_cli(cwd, "list")

            self.assertEqual("no sessions\n", result.stdout)

    def test_list_reports_sessions_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "alpha")
            self.run_cli(cwd, "start", "beta")
            with sqlite3.connect(cwd / ".harness" / "harness.db") as conn:
                conn.execute("UPDATE sessions SET updated_at = ? WHERE session_id = ?", ("2026-01-01T00:00:00+00:00", "alpha"))
                conn.execute("UPDATE sessions SET updated_at = ? WHERE session_id = ?", ("2026-01-02T00:00:00+00:00", "beta"))

            result = self.run_cli(cwd, "list")

            lines = result.stdout.splitlines()
            self.assertEqual("session_id\tstate\tupdated_at\trecovery_attempts\tartifact", lines[0])
            self.assertTrue(lines[1].startswith("beta\tstart\t2026-01-02T00:00:00+00:00\t0\t"))
            self.assertTrue(lines[2].startswith("alpha\tstart\t2026-01-01T00:00:00+00:00\t0\t"))
            self.assertIn(".harness/sessions/beta/artifact.md", lines[1])
            self.assertIn(".harness/sessions/alpha/artifact.md", lines[2])

    def test_start_strips_legacy_linear_template_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            template = cwd / ".harness" / "templates" / "session.md"
            template.write_text(template.read_text().replace('status: "start"\n', 'status: "start"\nlinear_issue_key: "{{LINEAR_ISSUE_KEY}}"\nlinear_issue_url: "{{LINEAR_ISSUE_URL}}"\n'))

            self.run_cli(cwd, "start", "req-login-timeout")

            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            self.assertNotIn("linear_issue_key", artifact.read_text())
            self.assertNotIn("linear_issue_url", artifact.read_text())

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
            text = text.replace("- [ ] TBD", "- [ ] Acceptance: download flow works", 1)
            text = text.replace("- [ ] TBD", "- [ ] Validate download flow", 1)
            text = text.replace("- [ ] TBD", "- [ ] Implement download flow", 1)
            text = self.with_guidance(text)
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
            approved_text = artifact.read_text()
            self.assertIn("- [x] Acceptance: download flow works", approved_text)
            self.assertIn("- [ ] Validate download flow", approved_text)
            self.assertIn("- [ ] Implement download flow", approved_text)

    def test_planning_to_implementation_does_not_require_checked_implementation_items(self):
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
            artifact.write_text(self.with_guidance(text))
            (cwd / "app.py").write_text("changed before implementation\n")

            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem")
            result = self.run_cli(cwd, "transition", "req-login-timeout", "implementation", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("non-harness changes already exist before implementation gate", result.stdout)
            self.assertNotIn("Implementation Checklist has unchecked items", result.stdout)

    def test_planning_to_implementation_allows_harness_generated_sync_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.git(cwd, "init", "-b", "main")
            self.git(cwd, "config", "user.email", "test@example.com")
            self.git(cwd, "config", "user.name", "Harness Test")
            self.run_cli(cwd, "start", "req-login-timeout")
            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            text = artifact.read_text()
            text = text.replace("TBD", "Download Neraca as Excel", 1)
            text = text.replace("- [ ] TBD", "- [ ] Acceptance exists", 1)
            text = text.replace("- [ ] TBD", "- [ ] Validation exists", 1)
            text = text.replace("- [ ] TBD", "- [ ] Implementation task", 1)
            artifact.write_text(self.with_guidance(text))

            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem")
            result = self.run_cli(cwd, "transition", "req-login-timeout", "implementation")

            self.assertIn("transitioned: planning -> implementation", result.stdout)

    def test_approve_planning_defaults_to_whoami(self):
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
            artifact.write_text(self.with_guidance(text))

            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            result = self.run_cli(cwd, "approve-planning", "req-login-timeout")
            expected_name = subprocess.run(
                ["whoami"],
                text=True,
                stdout=subprocess.PIPE,
                check=True,
            ).stdout.strip()

            self.assertIn(f"planning approved by {expected_name}", result.stdout)
            self.assertIn(f'planning_approved_by: "{expected_name}"', artifact.read_text())

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
            self.assertIn("Implementation Guidance must be filled", result.stdout)
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
            self.assertIn("Implementation Guidance must be filled", result.stdout)
            self.assertIn("Implementation Checklist must be filled", result.stdout)

    def test_approve_planning_requires_implementation_sketch(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")
            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            text = artifact.read_text()
            text = text.replace("TBD", "Download Neraca as Excel", 1)
            text = text.replace("- [ ] TBD", "- [ ] Acceptance exists", 1)
            text = text.replace("- [ ] TBD", "- [ ] Run validation", 1)
            text = text.replace(
                self.guidance_placeholder(),
                "\n".join(
                    [
                        "## Implementation Guidance",
                        "",
                        "Use the existing controller and service style.",
                        "",
                        "### Old Flow",
                        "",
                        "```mermaid",
                        "sequenceDiagram",
                        "    participant Client",
                        "    participant ReportController_php",
                        "    Client->>ReportController_php: request",
                        "```",
                        "",
                        "### New Flow",
                        "",
                        "```mermaid",
                        "sequenceDiagram",
                        "    participant Client",
                        "    participant ReportController_php",
                        "    Client->>ReportController_php: request",
                        "```",
                        "",
                    ]
                ),
                1,
            )
            text = text.replace("- [ ] TBD", "- [ ] Implement download flow", 1)
            artifact.write_text(text)

            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            result = self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Implementation Guidance must include an Implementation Sketch", result.stdout)

    def test_approve_planning_requires_mermaid_sequence_flows(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")
            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            text = artifact.read_text()
            text = text.replace("TBD", "Download Neraca as Excel", 1)
            text = text.replace("- [ ] TBD", "- [ ] Acceptance exists", 1)
            text = text.replace("- [ ] TBD", "- [ ] Run validation", 1)
            text = text.replace(
                self.guidance_placeholder(),
                "\n".join(
                    [
                        "## Implementation Guidance",
                        "",
                        "Expected location: controller.",
                        "",
                        "### Old Flow",
                        "",
                        "```mermaid",
                        "sequenceDiagram",
                        "    participant Client",
                        "    participant ReportController_php",
                        "    Client->>ReportController_php: request",
                        "    alt scoped behavior applies",
                        "        ReportController_php->>ReportController_php: apply scoped behavior change",
                        "    else existing behavior",
                        "        ReportController_php->>ReportController_php: preserve existing behavior",
                        "    end",
                        "```",
                        "",
                        "### New Flow",
                        "",
                        "Client->>ReportController_php: request with new behavior",
                        "",
                        "### Implementation Sketch",
                        "",
                        "Pseudocode: change the selected branch only.",
                        "",
                        "### Code Anchors",
                        "",
                        "- Existing controller condition.",
                    ]
                ),
                1,
            )
            text = text.replace("- [ ] TBD", "- [ ] Implement download flow", 1)
            artifact.write_text(text)

            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            result = self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Implementation Guidance must include a New Flow Mermaid sequence diagram showing target behavior", result.stdout)

    def test_approve_planning_accepts_tilde_mermaid_sequence_flows(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")
            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            text = artifact.read_text()
            text = text.replace("TBD", "Download Neraca as Excel", 1)
            text = text.replace("- [ ] TBD", "- [ ] Acceptance exists", 1)
            text = text.replace("- [ ] TBD", "- [ ] Run validation", 1)
            text = text.replace(
                self.guidance_placeholder(),
                "\n".join(
                    [
                        "## Implementation Guidance",
                        "",
                        "Expected location: controller.",
                        "",
                        "### Old Flow",
                        "",
                        "~~~mermaid",
                        "sequenceDiagram",
                        "    participant Client",
                        "    participant ReportController_php",
                        "    Client->>ReportController_php: request",
                        "    ReportController_php->>ReportController_php: current behavior",
                        "~~~",
                        "",
                        "### New Flow",
                        "",
                        "~~~mermaid",
                        "sequenceDiagram",
                        "    participant Client",
                        "    participant ReportController_php",
                        "    Client->>ReportController_php: request",
                        "    alt scoped behavior applies",
                        "        ReportController_php->>ReportController_php: apply scoped behavior change",
                        "    else existing behavior",
                        "        ReportController_php->>ReportController_php: preserve existing behavior",
                        "    end",
                        "~~~",
                        "",
                        "### Implementation Sketch",
                        "",
                        "Pseudocode: change the selected branch only.",
                        "",
                        "### Code Anchors",
                        "",
                        "- Existing controller condition.",
                    ]
                ),
                1,
            )
            text = text.replace("- [ ] TBD", "- [ ] Implement download flow", 1)
            artifact.write_text(text)

            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            result = self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem")

            self.assertIn("planning approved by Liem", result.stdout)

    def test_approve_planning_requires_code_anchors(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")
            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            text = artifact.read_text()
            text = text.replace("TBD", "Download Neraca as Excel", 1)
            text = text.replace("- [ ] TBD", "- [ ] Acceptance exists", 1)
            text = text.replace("- [ ] TBD", "- [ ] Run validation", 1)
            text = text.replace(
                self.guidance_placeholder(),
                "\n".join(
                    [
                        "## Implementation Guidance",
                        "",
                        "Expected location: controller.",
                        "",
                        "### Old Flow",
                        "",
                        "```mermaid",
                        "sequenceDiagram",
                        "    participant Client",
                        "    participant ReportController_php",
                        "    Client->>ReportController_php: request",
                        "    ReportController_php->>ReportController_php: current behavior",
                        "```",
                        "",
                        "### New Flow",
                        "",
                        "```mermaid",
                        "sequenceDiagram",
                        "    participant Client",
                        "    participant ReportController_php",
                        "    Client->>ReportController_php: request",
                        "    alt scoped behavior applies",
                        "        ReportController_php->>ReportController_php: apply scoped behavior change",
                        "    else existing behavior",
                        "        ReportController_php->>ReportController_php: preserve existing behavior",
                        "    end",
                        "```",
                        "",
                        "### Implementation Sketch",
                        "",
                        "Pseudocode: change the selected branch only.",
                    ]
                ),
                1,
            )
            text = text.replace("- [ ] TBD", "- [ ] Implement download flow", 1)
            artifact.write_text(text)

            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            result = self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Implementation Guidance must include Code Anchors", result.stdout)

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
            artifact.write_text(self.with_guidance(text))

            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem")
            self.run_cli(cwd, "transition", "req-login-timeout", "implementation")
            artifact.write_text(artifact.read_text().replace("- [x] Acceptance exists", "- [x] Acceptance changed"))

            blocked = self.run_cli(cwd, "preflight-edit", "req-login-timeout", check=False)

            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("Planning sections changed after approval", blocked.stdout)

    def test_checking_implementation_items_does_not_invalidate_planning_approval(self):
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
            artifact.write_text(self.with_guidance(text))

            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem")
            self.run_cli(cwd, "transition", "req-login-timeout", "implementation")
            artifact.write_text(artifact.read_text().replace("- [ ] Implementation task", "- [x] Implementation task"))

            allowed = self.run_cli(cwd, "preflight-edit", "req-login-timeout")

            self.assertIn("edit preflight allowed", allowed.stdout)

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
            artifact.write_text(self.with_guidance(text))

            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem")
            self.run_cli(cwd, "transition", "req-login-timeout", "implementation")
            (cwd / "app.py").write_text("changed\n")
            result = self.run_cli(cwd, "validate", "req-login-timeout", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Implementation Checklist has unchecked items while product changes exist", result.stdout)

    def test_modified_gitignore_does_not_count_as_product_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            subprocess.run(["git", "init"], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            self.run_cli(cwd, "init")
            subprocess.run(["git", "add", ".gitignore"], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            subprocess.run(
                ["git", "commit", "-m", "seed gitignore"],
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                env={**os.environ, "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com", "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com"},
            )
            self.run_cli(cwd, "start", "req-login-timeout")
            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            text = artifact.read_text()
            text = text.replace("TBD", "Download Neraca as Excel", 1)
            text = text.replace("- [ ] TBD", "- [ ] Acceptance exists", 1)
            text = text.replace("- [ ] TBD", "- [ ] Validation exists", 1)
            text = text.replace("- [ ] TBD", "- [ ] Implementation task", 1)
            artifact.write_text(self.with_guidance(text))

            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem")
            self.run_cli(cwd, "transition", "req-login-timeout", "implementation")
            (cwd / ".gitignore").write_text((cwd / ".gitignore").read_text() + "local.tmp\n")
            result = self.run_cli(cwd, "validate", "req-login-timeout")

            self.assertIn("valid", result.stdout)

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
            artifact.write_text(self.with_guidance(text))

            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem")
            self.run_cli(cwd, "transition", "req-login-timeout", "implementation")
            result = self.run_cli(cwd, "transition", "req-login-timeout", "review", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Implementation Checklist must be fully checked before review", result.stdout)

    def test_record_review_writes_ai_review_from_argument(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            artifact = self.enter_review(cwd)
            html_artifact = artifact.with_suffix(".html")

            result = self.run_cli(cwd, "record-review", "req-login-timeout", "--ai", "No blocking issues.")

            self.assertIn("recorded AI review", result.stdout)
            text = artifact.read_text()
            self.assertIn("### AI Review", text)
            self.assertIn("#### Review pass", text)
            self.assertIn("No blocking issues.", text)
            self.assertIn("### Human Review\n\nTBD", text)
            self.assertIn("No blocking issues.", html_artifact.read_text())
            with sqlite3.connect(cwd / ".harness" / "harness.db") as conn:
                count = conn.execute("SELECT COUNT(*) FROM review_passes WHERE session_id = ?", ("req-login-timeout",)).fetchone()[0]
            self.assertEqual(1, count)

    def test_record_review_appends_file_and_human_selected_required_fixes(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            artifact = self.enter_review(cwd)
            review = cwd / "review.md"
            review.write_text("Found validation gap.\n")

            self.run_cli(
                cwd,
                "record-review",
                "req-login-timeout",
                "--file",
                str(review),
                "--required-fix",
                "Add missing validation test",
            )

            text = artifact.read_text()
            self.assertIn("Found validation gap.", text)
            self.assertIn("### Required Fixes", text)
            self.assertIn("- [ ] Add missing validation test", text)
            with sqlite3.connect(cwd / ".harness" / "harness.db") as conn:
                row = conn.execute("SELECT description, resolved FROM required_fixes WHERE session_id = ?", ("req-login-timeout",)).fetchone()
            self.assertEqual(("Add missing validation test", 0), row)

    def test_record_review_without_required_fix_leaves_required_fixes_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            artifact = self.enter_review(cwd)

            self.run_cli(cwd, "record-review", "req-login-timeout", "--ai", "P2: optional cleanup.")

            text = artifact.read_text()
            self.assertIn("P2: optional cleanup.", text)
            self.assertIn("### Required Fixes\n\nNone.", text)

    def test_record_review_requires_review_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")

            result = self.run_cli(cwd, "record-review", "req-login-timeout", "--ai", "No issues.", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("requires session state 'review'", result.stderr)

    def test_recover_moves_review_to_needs_fix_and_counts_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            artifact = self.enter_review(cwd)

            result = self.run_cli(cwd, "recover", "req-login-timeout", "--reason", "open review item")

            self.assertIn("recovery attempt recorded: 1/3", result.stdout)
            self.assertIn("transitioned: review -> needs-fix", result.stdout)
            self.assertIn('status: "needs-fix"', artifact.read_text())
            self.assertIn('recovery_attempts: "1"', artifact.read_text())

    def test_needs_fix_preflight_allows_fix_work_with_unchecked_items_and_product_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            artifact = self.enter_review(cwd)
            self.run_cli(cwd, "recover", "req-login-timeout", "--reason", "open review item")
            artifact.write_text(artifact.read_text().replace("- [x] Implementation complete", "- [ ] Implementation complete"))
            (cwd / "app.py").write_text("fix in progress\n")

            result = self.run_cli(cwd, "preflight-edit", "req-login-timeout")

            self.assertIn("edit preflight allowed", result.stdout)

    def test_needs_fix_transition_to_implementation_stays_strict_until_checklist_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            artifact = self.enter_review(cwd)
            self.run_cli(cwd, "recover", "req-login-timeout", "--reason", "open review item")
            artifact.write_text(artifact.read_text().replace("- [x] Implementation complete", "- [ ] Implementation complete"))
            (cwd / "app.py").write_text("fix in progress\n")

            blocked = self.run_cli(cwd, "transition", "req-login-timeout", "implementation", check=False)
            artifact.write_text(artifact.read_text().replace("- [ ] Implementation complete", "- [x] Implementation complete"))
            allowed = self.run_cli(cwd, "transition", "req-login-timeout", "implementation")

            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("Implementation Checklist has unchecked items while product changes exist", blocked.stdout)
            self.assertIn("transitioned: needs-fix -> implementation", allowed.stdout)

    def test_history_reports_audit_trail(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            review_file = cwd / "review.md"
            proof = cwd / "proof.txt"
            self.enter_review(cwd)
            review_file.write_text("Review found a validation gap.\nSecond line ignored.\n")
            proof.write_text("proof\n")
            self.run_cli(
                cwd,
                "record-review",
                "req-login-timeout",
                "--file",
                str(review_file),
                "--required-fix",
                "Add validation proof",
            )
            self.run_cli(cwd, "approve-review", "req-login-timeout", "--by", "Liem")
            self.run_cli(cwd, "attach-proof", "req-login-timeout", str(proof))
            self.run_cli(cwd, "recover", "req-login-timeout", "--reason", "open review item: Add validation proof")

            result = self.run_cli(cwd, "history", "req-login-timeout")

            self.assertIn("Session history: req-login-timeout", result.stdout)
            self.assertIn("Transitions", result.stdout)
            self.assertIn("start -> planning success", result.stdout)
            self.assertIn("review -> needs-fix recovery reason: open review item: Add validation proof", result.stdout)
            self.assertIn("Approvals", result.stdout)
            self.assertIn("planning by Liem", result.stdout)
            self.assertIn("review by Liem", result.stdout)
            self.assertIn("Review Passes", result.stdout)
            self.assertIn("Review found a validation gap. Second line ignored.", result.stdout)
            self.assertIn("Required Fixes", result.stdout)
            self.assertIn("open Add validation proof", result.stdout)
            self.assertIn("Proofs", result.stdout)
            self.assertIn("proof.txt", result.stdout)

    def test_history_unknown_session_fails_clearly(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")

            result = self.run_cli(cwd, "history", "missing", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("session not found in SQLite state store: missing", result.stderr)

    def test_recover_allows_three_attempts_then_blocks_on_next_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            artifact = self.enter_review(cwd)

            self.run_cli(cwd, "recover", "req-login-timeout", "--reason", "review item 1")
            self.run_cli(cwd, "recover", "req-login-timeout", "--reason", "review item 2")
            third = self.run_cli(cwd, "recover", "req-login-timeout", "--reason", "review item 3")

            self.assertIn("recovery attempt recorded: 3/3", third.stdout)
            self.assertIn('status: "needs-fix"', artifact.read_text())

            blocked = self.run_cli(cwd, "recover", "req-login-timeout", "--reason", "review item 4", check=False)

            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("recovery blocked: 3/3 attempts used", blocked.stdout)
            self.assertIn('status: "blocked"', artifact.read_text())

    def test_transition_out_of_blocked_resets_recovery_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            artifact = self.enter_review(cwd)
            self.run_cli(cwd, "recover", "req-login-timeout", "--reason", "review item 1")
            self.run_cli(cwd, "recover", "req-login-timeout", "--reason", "review item 2")
            self.run_cli(cwd, "recover", "req-login-timeout", "--reason", "review item 3")
            self.run_cli(cwd, "recover", "req-login-timeout", "--reason", "review item 4", check=False)

            result = self.run_cli(cwd, "transition", "req-login-timeout", "implementation")

            self.assertIn("transitioned: blocked -> implementation", result.stdout)
            self.assertIn('recovery_attempts: "0"', artifact.read_text())

    def test_recover_moves_quality_check_failure_to_needs_fix(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            artifact = self.enter_quality_check(cwd)

            result = self.run_cli(cwd, "recover", "req-login-timeout", "--reason", "unit test failed")

            self.assertIn("transitioned: quality-check -> needs-fix", result.stdout)
            self.assertIn('status: "needs-fix"', artifact.read_text())

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
            artifact.write_text(self.with_guidance(text))

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
            artifact.write_text(self.with_guidance(text))

            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem")
            self.run_cli(cwd, "transition", "req-login-timeout", "implementation")
            self.run_cli(cwd, "transition", "req-login-timeout", "review")

            text = artifact.read_text()
            text = text.replace("### AI Review\n\nTBD", "### AI Review\n\nNo blocking issues.")
            text = text.replace("### Human Review\n\nTBD", "### Human Review\n\nLooks correct.")
            artifact.write_text(self.with_guidance(text))

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
            artifact.write_text(self.with_guidance(text))

            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem")
            self.run_cli(cwd, "transition", "req-login-timeout", "implementation")
            self.run_cli(cwd, "transition", "req-login-timeout", "review")
            text = artifact.read_text()
            text = text.replace("### AI Review\n\nTBD", "### AI Review\n\nNo blocking issues.")
            text = text.replace("### Human Review\n\nTBD", "### Human Review\n\nLooks correct.")
            artifact.write_text(self.with_guidance(text))
            self.run_cli(cwd, "approve-review", "req-login-timeout", "--by", "Liem")
            self.run_cli(cwd, "transition", "req-login-timeout", "quality-check")

            result = self.run_cli(cwd, "validate", "req-login-timeout", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Validation Plan checklist must be executed", result.stdout)
            self.assertIn("Quality Check Commands Run", result.stdout)

    def test_executing_validation_plan_does_not_invalidate_planning_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")
            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            text = artifact.read_text()
            text = text.replace("TBD", "Download Neraca as Excel", 1)
            text = text.replace("- [ ] TBD", "- [ ] Acceptance exists", 1)
            text = text.replace("- [ ] TBD", "- [ ] Run validation", 1)
            text = text.replace("- [ ] TBD", "- [x] Implementation complete", 1)
            text = text.replace("### AI Review\n\nTBD", "### AI Review\n\nNo blocking issues.")
            text = text.replace("### Human Review\n\nTBD", "### Human Review\n\nLooks correct.")
            artifact.write_text(self.with_guidance(text))

            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem")
            self.run_cli(cwd, "transition", "req-login-timeout", "implementation")
            self.run_cli(cwd, "transition", "req-login-timeout", "review")
            self.run_cli(cwd, "approve-review", "req-login-timeout", "--by", "Liem")
            self.run_cli(cwd, "transition", "req-login-timeout", "quality-check")
            artifact.write_text(artifact.read_text().replace("- [ ] Run validation", "- [x] Run validation"))
            self.complete_quality_check(cwd, artifact)

            result = self.run_cli(cwd, "validate", "req-login-timeout", check=False)

            self.assertEqual(0, result.returncode)
            self.assertNotIn("Planning sections changed after approval", result.stdout)

    def test_upgrade_guardrails_overwrites_bootstrap(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            (cwd / "AGENTS.md").write_text("old\n")

            self.run_cli(cwd, "upgrade-guardrails")

            text = (cwd / "AGENTS.md").read_text()
            self.assertIn("preflight-edit", text)
            self.assertIn("If preflight blocks", text)
            self.assertIn("If unsure the setup is healthy", text)
            self.assertIn("harness list", text)
            self.assertIn("choose a short kebab-case session id", text)
            self.assertIn("harness start <session-id>", text)
            self.assertIn("harness validate <session-id>", text)
            self.assertIn("harness recover <session-id>", text)

    def test_sync_guardrails_aliases_update_with_deprecation_notice(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")

            result = self.run_cli(cwd, "sync-guardrails")

            self.assertEqual(result.returncode, 0)
            self.assertIn("sync-guardrails is deprecated; use `harness update`", result.stdout)
            self.assertIn("target guardrails synced", result.stdout)

    def test_update_overwrites_agent_files_and_reports_version_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            (cwd / "AGENTS.md").write_text("old\n")
            (cwd / ".harness" / "agents" / "implementation.md").write_text("old\n")
            (cwd / ".harness" / "version").write_text("0\n")

            result = self.run_cli(cwd, "update", "--skip-pull")

            self.assertIn("synced harness guardrails", result.stdout)
            self.assertIn("- AGENTS.md", result.stdout)
            self.assertIn("- .harness/version", result.stdout)
            self.assertIn(f"harness version: 0 -> {self.harness_module.HARNESS_VERSION}", result.stdout)
            self.assertIn("target guardrails synced", result.stdout)
            self.assertEqual(self.harness_module.HARNESS_VERSION, (cwd / ".harness" / "version").read_text().strip())
            self.assertIn("preflight-edit", (cwd / "AGENTS.md").read_text())
            self.assertIn("Implementation State Guardrails", (cwd / ".harness" / "agents" / "implementation.md").read_text())
            self.assertIn(".harness/project/index.md", (cwd / "AGENTS.md").read_text())
            common_text = (cwd / ".harness" / "agents" / "common.md").read_text()
            self.assertIn("harness list", common_text)
            self.assertIn("choose a short kebab-case session id", common_text)
            self.assertIn("harness start <session-id>", common_text)
            planning_text = (cwd / ".harness" / "agents" / "planning.md").read_text()
            self.assertIn("Read `.harness/project/index.md`", planning_text)
            self.assertIn("lower-capability implementation agent", planning_text)
            self.assertIn("Old Flow", planning_text)
            self.assertIn("New Flow", planning_text)
            self.assertIn("When revising `## Implementation Guidance`, re-check `### Old Flow` and `### New Flow`", planning_text)
            self.assertNotIn("Focused Changes Flow", planning_text)
            self.assertIn("Implementation Sketch", planning_text)
            self.assertNotIn("Decision Flow", planning_text)
            self.assertIn("Code Anchors", planning_text)
            implementation_text = (cwd / ".harness" / "agents" / "implementation.md").read_text()
            self.assertIn("Read `### Old Flow`", implementation_text)
            self.assertNotIn("Focused Changes Flow", implementation_text)
            self.assertIn("Follow the `### Implementation Sketch`", implementation_text)
            self.assertNotIn("Decision Flow", implementation_text)
            self.assertIn("Use `### Code Anchors`", implementation_text)
            self.assertTrue((cwd / ".harness" / "agents" / "needs-fix.md").exists())
            needs_fix_text = (cwd / ".harness" / "agents" / "needs-fix.md").read_text()
            self.assertIn("Needs-Fix State Guardrails", needs_fix_text)
            self.assertIn("harness history <session-id>", needs_fix_text)
            self.assertIn("harness transition <session-id> implementation", needs_fix_text)

    def test_start_warns_when_guardrails_are_outdated_but_still_creates_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            (cwd / ".harness" / "version").write_text("0\n")

            result = self.run_cli(cwd, "start", "req-login-timeout")

            self.assertIn("target guardrails are outdated; run harness update", result.stderr)
            self.assertTrue((cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md").exists())

    def test_start_does_not_warn_when_guardrails_are_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")

            result = self.run_cli(cwd, "start", "req-login-timeout")

            self.assertNotIn("target guardrails are outdated", result.stderr)

    def test_update_skip_pull_syncs_outdated_target_guardrails(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            (cwd / "AGENTS.md").write_text("old\n")
            (cwd / ".harness" / "version").write_text("0\n")

            result = self.run_cli(cwd, "update", "--skip-pull")

            self.assertIn("synced harness guardrails", result.stdout)
            self.assertIn("target guardrails synced", result.stdout)
            self.assertIn(f"harness version: 0 -> {self.harness_module.HARNESS_VERSION}", result.stdout)
            self.assertIn("Harness Agent Bootstrap", (cwd / "AGENTS.md").read_text())
            self.assertEqual(self.harness_module.HARNESS_VERSION, (cwd / ".harness" / "version").read_text().strip())

    def test_update_skip_pull_refreshes_when_target_guardrails_are_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")

            result = self.run_cli(cwd, "update", "--skip-pull")

            self.assertIn("synced harness guardrails", result.stdout)
            self.assertIn(f"harness version: {self.harness_module.HARNESS_VERSION} -> {self.harness_module.HARNESS_VERSION}", result.stdout)
            self.assertIn("target guardrails synced", result.stdout)

    def test_update_pulls_harness_source_when_behind_origin_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source, cli = self.make_harness_git_fixture(base)
            target = base / "target"
            target.mkdir()
            self.run_temp_cli(cli, target, "init")

            result = self.run_temp_cli(cli, target, "update")

            self.assertIn("pulled latest harness source", result.stdout)
            self.assertIn("target guardrails synced", result.stdout)
            self.assertEqual("v2\n", (source / "README.md").read_text())

    def test_update_aborts_before_pull_when_harness_source_is_dirty(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source, cli = self.make_harness_git_fixture(base)
            target = base / "target"
            target.mkdir()
            self.run_temp_cli(cli, target, "init")
            (source / "local.txt").write_text("dirty\n")

            result = self.run_temp_cli(cli, target, "update", check=False)

            self.assertNotEqual(0, result.returncode)
            self.assertIn("uncommitted changes", result.stderr)
            self.assertEqual("v1\n", (source / "README.md").read_text())

    def test_existing_agents_sample_is_used_as_bootstrap_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / "AGENTS_SAMPLE.md").write_text("old sample\n")

            self.run_cli(cwd, "init")

            self.assertFalse((cwd / "AGENTS.md").exists())
            drift = self.run_cli(cwd, "doctor", check=False)
            self.assertNotEqual(drift.returncode, 0)
            self.assertIn("AGENTS_SAMPLE.md", drift.stdout)

            result = self.run_cli(cwd, "update", "--skip-pull")
            self.assertIn("- AGENTS_SAMPLE.md", result.stdout)
            self.assertIn("Harness Agent Bootstrap", (cwd / "AGENTS_SAMPLE.md").read_text())
            self.assertFalse((cwd / "AGENTS.md").exists())

    def test_generated_guardrails_cover_every_state(self):
        generated = self.harness_module.default_agents()
        expected = {f"{state}.md" for state in self.harness_module.STATES}
        expected.add("common.md")
        self.assertEqual(expected, set(generated))

    def test_init_generates_guardrail_for_every_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")

            for state in self.harness_module.STATES:
                self.assertTrue((cwd / ".harness" / "agents" / f"{state}.md").exists(), state)

    def test_init_project_map_creates_missing_files_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            project = cwd / ".harness" / "project"
            project.mkdir(parents=True)
            (project / "overview.md").write_text("# Custom Overview\n\nKeep this.\n")

            result = self.run_cli(cwd, "init-project-map")

            self.assertIn("initialized project map", result.stdout)
            self.assertEqual("# Custom Overview\n\nKeep this.\n", (project / "overview.md").read_text())
            self.assertTrue((project / "architecture.md").exists())
            self.assertTrue((project / "index.md").exists())
            self.assertIn("Current code wins", (project / "index.md").read_text())

    def test_sync_project_map_requires_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init-project-map")

            result = self.run_cli(cwd, "sync-project-map", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--force", result.stderr)

    def test_sync_project_map_force_refreshes_templates_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            project = cwd / ".harness" / "project"
            (project / "validation.md").write_text("custom\n")
            session_dir = cwd / ".harness" / "sessions" / "req-login-timeout"
            session_dir.mkdir(parents=True)
            artifact = session_dir / "artifact.md"
            artifact.write_text("session artifact\n")

            result = self.run_cli(cwd, "sync-project-map", "--force")

            self.assertIn("synced project map", result.stdout)
            self.assertIn("Build Commands", (project / "validation.md").read_text())
            self.assertEqual("session artifact\n", artifact.read_text())

    def test_backend_quality_gate_requires_curl_and_sample_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            artifact = self.enter_quality_check(cwd, "Backend API validation")
            config = cwd / ".harness" / "harness.yml"
            config.write_text(config.read_text().replace("required_proof: auto", "required_proof: backend"))
            proof = cwd / "backend-proof.txt"
            proof.write_text("ok\n")
            self.run_cli(cwd, "attach-proof", "req-login-timeout", str(proof))
            text = artifact.read_text()
            text = text.replace("### Commands Run\n\nTBD", "### Commands Run\n\n- php artisan test: PASS")
            artifact.write_text(self.with_guidance(text))

            result = self.run_cli(cwd, "validate", "req-login-timeout", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Backend proof requires a curl command", result.stdout)
            self.assertIn("Backend proof requires a sample response", result.stdout)

            text = artifact.read_text()
            text = text.replace(
                "### Commands Run\n\n- php artisan test: PASS",
                "### Commands Run\n\n- curl -i http://localhost/api/neraca\n- Sample response: HTTP/1.1 200 OK {\"ok\":true}",
            )
            artifact.write_text(self.with_guidance(text))
            self.assertEqual(0, self.run_cli(cwd, "validate", "req-login-timeout").returncode)

    def test_frontend_quality_gate_requires_screenshot_and_view_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            artifact = self.enter_quality_check(cwd, "Frontend UI validation")
            config = cwd / ".harness" / "harness.yml"
            config.write_text(config.read_text().replace("required_proof: auto", "required_proof: frontend"))
            proof = cwd / "result.txt"
            proof.write_text("ok\n")
            self.run_cli(cwd, "attach-proof", "req-login-timeout", str(proof))
            text = artifact.read_text()
            text = text.replace("### Commands Run\n\nTBD", "### Commands Run\n\n- npm test: PASS")
            artifact.write_text(self.with_guidance(text))

            result = self.run_cli(cwd, "validate", "req-login-timeout", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Frontend proof requires screenshot proof", result.stdout)
            self.assertIn("Frontend proof requires view validation", result.stdout)

            screenshot = cwd / "screenshot.png"
            screenshot.write_text("png\n")
            self.run_cli(cwd, "attach-proof", "req-login-timeout", str(screenshot))
            text = artifact.read_text()
            text = text.replace("### Manual Validation\n\nTBD", "### Manual Validation\n\nView validated in browser.")
            artifact.write_text(self.with_guidance(text))
            self.assertEqual(0, self.run_cli(cwd, "validate", "req-login-timeout").returncode)

    def test_both_quality_gate_requires_backend_and_frontend_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            artifact = self.enter_quality_check(cwd, "Full stack validation")
            config = cwd / ".harness" / "harness.yml"
            config.write_text(config.read_text().replace("required_proof: auto", "required_proof: both"))
            screenshot = cwd / "screenshot.png"
            screenshot.write_text("png\n")
            self.run_cli(cwd, "attach-proof", "req-login-timeout", str(screenshot))
            text = artifact.read_text()
            text = text.replace(
                "### Commands Run\n\nTBD",
                "### Commands Run\n\n- curl -i http://localhost/api/neraca\n- Sample response: status 200",
            )
            text = text.replace("### Manual Validation\n\nTBD", "### Manual Validation\n\nView validated in browser.")
            artifact.write_text(self.with_guidance(text))

            self.assertEqual(0, self.run_cli(cwd, "validate", "req-login-timeout").returncode)

    def test_quality_check_transitions_to_approval_after_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            artifact = self.enter_quality_check(cwd)
            self.complete_quality_check(cwd, artifact)

            result = self.run_cli(cwd, "transition", "req-login-timeout", "approval")

            self.assertIn("transitioned: quality-check -> approval", result.stdout)
            self.assertIn('status: "approval"', artifact.read_text())

    def test_done_requires_quality_approval_after_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            artifact = self.enter_quality_check(cwd)
            self.complete_quality_check(cwd, artifact)
            self.run_cli(cwd, "transition", "req-login-timeout", "approval")

            result = self.run_cli(cwd, "transition", "req-login-timeout", "done", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Quality evidence must be approved", result.stdout)

    def test_approve_quality_requires_complete_quality_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            artifact = self.enter_quality_check(cwd)
            self.complete_quality_check(cwd, artifact)
            self.run_cli(cwd, "transition", "req-login-timeout", "approval")
            text = artifact.read_text()
            text = text.replace(
                "### Commands Run\n\n- curl -i http://localhost/api/neraca\n- Sample response: status 200",
                "### Commands Run\n\nTBD",
            )
            artifact.write_text(self.with_guidance(text))

            result = self.run_cli(cwd, "approve-quality", "req-login-timeout", "--by", "Liem", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("quality approval blocked", result.stdout)
            self.assertIn("Quality Check Commands Run must record validation commands/results", result.stdout)

    def test_approve_quality_records_final_approval_and_allows_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            artifact = self.enter_quality_check(cwd)
            self.complete_quality_check(cwd, artifact)
            self.run_cli(cwd, "transition", "req-login-timeout", "approval")

            result = self.run_cli(cwd, "approve-quality", "req-login-timeout", "--by", "Liem")
            done = self.run_cli(cwd, "transition", "req-login-timeout", "done")

            self.assertIn("quality approved by Liem", result.stdout)
            text = artifact.read_text()
            self.assertIn('quality_approved: "true"', text)
            self.assertIn('quality_approved_by: "Liem"', text)
            self.assertIn("## Final Approval\n\nApproved by Liem", text)
            self.assertIn("transitioned: approval -> done", done.stdout)

    def test_quality_recovery_clears_quality_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            artifact = self.enter_quality_check(cwd)
            self.complete_quality_check(cwd, artifact)
            self.run_cli(cwd, "transition", "req-login-timeout", "approval")
            self.run_cli(cwd, "approve-quality", "req-login-timeout", "--by", "Liem")

            result = self.run_cli(cwd, "recover", "req-login-timeout", "--reason", "approval rejected")

            self.assertIn("transitioned: approval -> needs-fix", result.stdout)
            text = artifact.read_text()
            self.assertIn('quality_approved: "false"', text)
            self.assertIn('quality_approved_by: ""', text)
            self.assertIn("## Final Approval\n\nTBD", text)

    def test_linear_commands_are_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")

            start = self.run_cli(cwd, "start", "req-login-timeout", "--linear", "WF-123", check=False)
            sync = self.run_cli(cwd, "sync-linear", "req-login-timeout", check=False)

            self.assertNotEqual(start.returncode, 0)
            self.assertNotEqual(sync.returncode, 0)
            self.assertIn("unrecognized arguments: --linear", start.stderr)
            self.assertIn("invalid choice", sync.stderr)

    def test_transition_updates_sqlite_and_artifact_mirror(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")
            self.run_cli(cwd, "transition", "req-login-timeout", "planning")

            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            self.assertIn('status: "planning"', artifact.read_text())
            with sqlite3.connect(cwd / ".harness" / "harness.db") as conn:
                state = conn.execute("SELECT state FROM sessions WHERE session_id = ?", ("req-login-timeout",)).fetchone()[0]
                transition_count = conn.execute("SELECT COUNT(*) FROM transitions").fetchone()[0]
            self.assertEqual("planning", state)
            self.assertEqual(1, transition_count)

    def test_sqlite_state_wins_over_artifact_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")
            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            artifact.write_text(artifact.read_text().replace('status: "planning"', 'status: "done"'))

            result = self.run_cli(cwd, "status", "req-login-timeout")

            self.assertIn("State: planning", result.stdout)

    def test_migrate_sqlite_imports_existing_markdown_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            db = cwd / ".harness" / "harness.db"
            db.unlink()
            artifact = cwd / ".harness" / "sessions" / "legacy" / "artifact.md"
            artifact.parent.mkdir(parents=True)
            artifact.write_text('---\nsession_id: "legacy"\nstatus: "review"\ncreated_at: "2026-01-01T00:00:00+00:00"\nupdated_at: "2026-01-01T00:00:00+00:00"\n---\n# Legacy\n')

            result = self.run_cli(cwd, "migrate-sqlite")

            self.assertIn("migrated sessions: 1", result.stdout)
            with sqlite3.connect(db) as conn:
                row = conn.execute("SELECT state FROM sessions WHERE session_id = ?", ("legacy",)).fetchone()
            self.assertEqual(("review",), row)

    def test_doctor_reports_artifact_status_mirror_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")
            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            artifact.write_text(artifact.read_text().replace('status: "planning"', 'status: "done"'))

            result = self.run_cli(cwd, "doctor", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("differs from SQLite state", result.stdout)

    def test_doctor_initializes_missing_sqlite_store_for_existing_scaffold(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            db = cwd / ".harness" / "harness.db"
            db.unlink()

            result = self.run_cli(cwd, "doctor")

            self.assertIn("initialized missing SQLite state store", result.stdout)
            self.assertIn("doctor ok", result.stdout)
            self.assertTrue(db.exists())

    def test_doctor_reports_generated_guardrail_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            (cwd / ".harness" / "agents" / "needs-fix.md").write_text("stale\n")

            result = self.run_cli(cwd, "doctor", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("guardrail drift", result.stdout)
            self.assertIn("needs-fix.md", result.stdout)

    def test_doctor_reports_bootstrap_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            (cwd / "AGENTS.md").write_text("stale\n")

            result = self.run_cli(cwd, "doctor", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("bootstrap drift", result.stdout)

    def test_doctor_reports_config_state_and_gitignore_issues(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            config = cwd / ".harness" / "harness.yml"
            config.write_text(config.read_text().replace("  - needs-fix\n", ""))
            gitignore = cwd / ".gitignore"
            gitignore.write_text(".env\n")

            result = self.run_cli(cwd, "doctor", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("config states differ from CLI STATES", result.stdout)
            self.assertIn(".gitignore missing .harness/harness.db", result.stdout)

    def test_doctor_reports_missing_template_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            template = cwd / ".harness" / "templates" / "session.md"
            template.write_text(template.read_text().replace("## Validation Plan", "## Removed Validation Plan"))

            result = self.run_cli(cwd, "doctor", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("session template missing ## Validation Plan", result.stdout)

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
            with sqlite3.connect(cwd / ".harness" / "harness.db") as conn:
                row = conn.execute("SELECT path FROM proofs WHERE session_id = ?", ("req-login-timeout",)).fetchone()
            self.assertTrue(row[0].endswith("proof/result.txt"))

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
            artifact.write_text(self.with_guidance(text))

            self.run_cli(cwd, "transition", "req-login-timeout", "planning")
            self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem")
            self.run_cli(cwd, "transition", "req-login-timeout", "implementation")
            self.run_cli(cwd, "transition", "req-login-timeout", "review")
            self.run_cli(cwd, "approve-review", "req-login-timeout", "--by", "Liem")
            self.run_cli(cwd, "transition", "req-login-timeout", "quality-check")
            text = artifact.read_text()
            text = text.replace("### Commands Run\n\nTBD", "### Commands Run\n\n- build ok")
            text = text.replace("### Proof\n\n- [ ] TBD", "### Proof\n\n- [x] [missing.pdf](proof/missing.pdf)")
            artifact.write_text(self.with_guidance(text))
            result = self.run_cli(cwd, "transition", "req-login-timeout", "approval", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Quality Check Proof needs at least one checked proof file under proof/", result.stdout)


if __name__ == "__main__":
    unittest.main()
