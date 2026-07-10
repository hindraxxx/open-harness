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
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "harness"
INSTALLER = ROOT / "install.sh"


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
        command_env["HARNESS_SKIP_USER_SUBAGENTS"] = "1"
        command_env["HARNESS_AUTO_SERVE"] = "0"
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
        command_env["HARNESS_SKIP_USER_SUBAGENTS"] = "1"
        command_env["HARNESS_AUTO_SERVE"] = "0"
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
        shutil.copytree(ROOT / ".harness" / "agents", seed / ".harness" / "agents")
        shutil.copytree(ROOT / ".harness" / "skills", seed / ".harness" / "skills")
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

    def make_installer_source_fixture(self, tmp: Path) -> Path:
        source = tmp / "installer-source"
        (source / "bin").mkdir(parents=True)
        shutil.copy2(CLI, source / "bin" / "harness")
        shutil.copy2(INSTALLER, source / "install.sh")
        shutil.copytree(ROOT / ".harness" / "agents", source / ".harness" / "agents")
        shutil.copytree(ROOT / ".harness" / "skills", source / ".harness" / "skills")
        os.chmod(source / "bin" / "harness", 0o755)
        os.chmod(source / "install.sh", 0o755)
        (source / "README.md").write_text("installer fixture\n")
        self.git(source, "init", "-b", "main")
        self.git(source, "config", "user.email", "test@example.com")
        self.git(source, "config", "user.name", "Harness Test")
        self.git(source, "add", ".")
        self.git(source, "commit", "-m", "initial")
        return source

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
            self.assertIn("If `harness` is not available", (cwd / "AGENTS.md").read_text())
            self.assertIn(".env", (cwd / ".gitignore").read_text().splitlines())
            self.assertEqual(self.harness_module.HARNESS_VERSION, (cwd / ".harness" / "version").read_text().strip())
            self.assertIn(f"harness version: none -> {self.harness_module.HARNESS_VERSION}", result.stdout)

    def test_init_installs_sub_agent_orchestration_in_common_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            common_md = (cwd / ".harness" / "agents" / "common.md").read_text()
            self.assertIn("## Sub-Agent Orchestration", common_md)
            self.assertIn("code-explorer", common_md)
            self.assertIn("implementer", common_md)
            self.assertIn("code-reviewer", common_md)

    def test_init_installs_sub_agent_orchestration_in_agents_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            agents_md = (cwd / "AGENTS.md").read_text()
            self.assertIn("Sub-Agent Orchestration", agents_md)

    def test_start_uses_local_session_id_and_sqlite_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            result = self.run_cli(cwd, "start", "req-login-timeout")
            created_line = next(line for line in result.stdout.splitlines() if line.startswith("created session: "))
            session_id = created_line.removeprefix("created session: ")
            self.assertRegex(session_id, r"^\d{8}_req-login-timeout$")

            artifact = cwd / ".harness" / "sessions" / session_id / "artifact.md"
            html_artifact = artifact.with_suffix(".html")
            self.assertTrue(artifact.exists())
            self.assertTrue(html_artifact.exists())
            self.assertTrue((artifact.parent / "proof").is_dir())
            text = artifact.read_text()
            self.assertIn(f'session_id: "{session_id}"', text)
            self.assertIn("## Implementation Guidance", text)
            self.assertNotIn("linear_issue_key", text)
            html_text = html_artifact.read_text()
            self.assertIn(f"Harness Artifact: {session_id}", html_text)
            self.assertIn("<span>Implementation Guidance</span>", html_text)
            self.assertIn('<div class="mermaid">sequenceDiagram', html_text)
            self.assertIn("cdn.jsdelivr.net/npm/mermaid", html_text)
            with sqlite3.connect(cwd / ".harness" / "harness.db") as conn:
                row = conn.execute("SELECT state FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
            self.assertEqual(("start",), row)

    def test_start_keeps_existing_date_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")

            result = self.run_cli(cwd, "start", "20260605_req-login-timeout")

            self.assertIn("created session: 20260605_req-login-timeout", result.stdout)
            artifact = cwd / ".harness" / "sessions" / "20260605_req-login-timeout" / "artifact.md"
            self.assertTrue(artifact.exists())
            self.assertIn('session_id: "20260605_req-login-timeout"', artifact.read_text())

    def test_plan_epic_split_flag_creates_child_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")

            result = self.run_cli(
                cwd,
                "plan-epic",
                "epic-approval",
                "--split-stories",
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
            index_html_text = index_html.read_text()
            self.assertIn("children/story-001/plan.html", index_html_text)
            self.assertIn("Repo Session", index_html_text)
            self.assertIn("not linked", index_html_text)
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
            self.assertEqual("", metadata["target_repo"])
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

    def test_plan_epic_defaults_three_stories_to_single_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")

            result = self.run_cli(
                cwd,
                "plan-epic",
                "epic-three",
                "--story",
                "story-001:First behavior",
                "--story",
                "story-002:Second behavior",
                "--story",
                "story-003:Third behavior",
            )

            epic = cwd / ".harness" / "sessions" / "epic-three"
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
            self.assertRegex(result.stdout, r"split session: \d{8}_epic-approval")
            self.assertIn("parent artifact:", result.stdout)
            self.assertTrue((epic / "artifact.md").exists())
            self.assertTrue((epic / "artifact.html").exists())
            self.assertTrue((epic / "index.html").exists())
            self.assertTrue((epic / "epic-plan.md").exists())
            self.assertTrue((epic / "synthesis.md").exists())
            self.assertTrue((epic / "children" / "story-001" / "plan.md").exists())
            self.assertTrue((epic / "children" / "story-001" / "plan.html").exists())
            session_id = self.harness_module.parse_frontmatter((epic / "artifact.md").read_text())[0]["session_id"]
            metadata = json.loads((epic / "children" / "story-001" / "metadata.json").read_text())
            self.assertEqual(session_id, metadata["epic_id"])
            self.assertEqual("story-001", metadata["story_id"])
            self.assertEqual("children/story-001/plan.md", metadata["plan_md"])
            with sqlite3.connect(cwd / ".harness" / "harness.db") as conn:
                row = conn.execute("SELECT state FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
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

    def test_start_story_creates_repo_local_planning_session_and_links_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            coordinator = Path(tmp) / "coordinator"
            target_repo = Path(tmp) / "target-repo"
            coordinator.mkdir()
            target_repo.mkdir()
            self.run_cli(coordinator, "init")
            self.run_cli(target_repo, "init")
            self.run_cli(
                coordinator,
                "plan-epic",
                "epic-approval",
                "--split-stories",
                "--story",
                "story-001:Maker submits request",
            )
            story_plan = coordinator / ".harness" / "sessions" / "epic-approval" / "children" / "story-001" / "plan.md"
            story_plan.write_text(
                story_plan.read_text().replace(
                    "## Open Questions\n\n- [ ] TBD",
                    "\n".join(
                        [
                            "## Code Anchors",
                            "",
                            "- `src/main/kotlin/App.kt` lines 10-24; compact check: `sed -n '10,24p' src/main/kotlin/App.kt`.",
                            "- `src/test/kotlin/AppTest.kt` matcher anchor; compact check: `rg -n \"default payment\" src/test/kotlin/AppTest.kt`.",
                            "",
                            "## Open Questions",
                            "",
                            "- [ ] TBD",
                        ]
                    ),
                )
            )

            result = self.run_cli(
                coordinator,
                "start-story",
                "story-001",
                "--repo",
                str(target_repo),
                "--session-id",
                "20260630_story-001",
            )

            self.assertIn("started story session: 20260630_story-001", result.stdout)
            target_artifact = target_repo / ".harness" / "sessions" / "20260630_story-001" / "artifact.md"
            self.assertTrue(target_artifact.exists())
            target_text = target_artifact.read_text()
            self.assertIn('status: "planning"', target_text)
            self.assertIn("Repo-local implementation session for child story `story-001`", target_text)
            self.assertIn("This session is scoped to", target_text)
            self.assertIn("sed -n '10,24p' src/main/kotlin/App.kt", target_text)
            self.assertIn('rg -n "default payment" src/test/kotlin/AppTest.kt', target_text)
            with sqlite3.connect(target_repo / ".harness" / "harness.db") as conn:
                row = conn.execute("SELECT state FROM sessions WHERE session_id = ?", ("20260630_story-001",)).fetchone()
            self.assertEqual(("planning",), row)

            metadata_path = coordinator / ".harness" / "sessions" / "epic-approval" / "children" / "story-001" / "metadata.json"
            metadata = json.loads(metadata_path.read_text())
            self.assertEqual("20260630_story-001", metadata["planning_session_id"])
            self.assertEqual(str(target_repo.resolve()), metadata["target_repo"])
            self.assertEqual("planning", metadata["status"])
            index_html = coordinator / ".harness" / "sessions" / "epic-approval" / "index.html"
            index_html_text = index_html.read_text()
            self.assertIn("target-repo", index_html_text)
            self.assertIn("20260630_story-001", index_html_text)
            self.assertIn((target_artifact.with_suffix(".html")).resolve().as_uri(), index_html_text)

    def test_start_story_can_scope_duplicate_story_id_by_epic(self):
        with tempfile.TemporaryDirectory() as tmp:
            coordinator = Path(tmp) / "coordinator"
            target_repo = Path(tmp) / "target-repo"
            coordinator.mkdir()
            target_repo.mkdir()
            self.run_cli(coordinator, "init")
            self.run_cli(target_repo, "init")
            for epic_id in ["older-epic", "active-epic"]:
                self.run_cli(
                    coordinator,
                    "plan-epic",
                    epic_id,
                    "--split-stories",
                    "--story",
                    "story-001:Maker submits request",
                )

            ambiguous = self.run_cli(
                coordinator,
                "start-story",
                "story-001",
                "--repo",
                str(target_repo),
                "--session-id",
                "20260630_story-001",
                check=False,
            )
            self.assertNotEqual(0, ambiguous.returncode)
            self.assertIn("story id is ambiguous across epics", ambiguous.stderr)

            result = self.run_cli(
                coordinator,
                "start-story",
                "story-001",
                "--epic",
                "active-epic",
                "--repo",
                str(target_repo),
                "--session-id",
                "20260630_story-001",
            )

            self.assertIn("started story session: 20260630_story-001", result.stdout)
            active_metadata = coordinator / ".harness" / "sessions" / "active-epic" / "children" / "story-001" / "metadata.json"
            older_metadata = coordinator / ".harness" / "sessions" / "older-epic" / "children" / "story-001" / "metadata.json"
            self.assertEqual("20260630_story-001", json.loads(active_metadata.read_text())["planning_session_id"])
            self.assertEqual("", json.loads(older_metadata.read_text())["planning_session_id"])

    def test_link_story_connects_parent_index_to_existing_repo_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            coordinator = Path(tmp) / "coordinator"
            target_repo = Path(tmp) / "target-repo"
            coordinator.mkdir()
            target_repo.mkdir()
            self.run_cli(coordinator, "init")
            self.run_cli(target_repo, "init")
            self.run_cli(target_repo, "start", "20260630_existing-story-session")
            self.run_cli(
                coordinator,
                "plan-epic",
                "epic-approval",
                "--split-stories",
                "--story",
                "story-001:Maker submits request",
            )

            result = self.run_cli(
                coordinator,
                "link-story",
                "story-001",
                "--repo",
                str(target_repo),
                "--session-id",
                "20260630_existing-story-session",
            )

            self.assertIn("linked story session: 20260630_existing-story-session", result.stdout)
            metadata_path = coordinator / ".harness" / "sessions" / "epic-approval" / "children" / "story-001" / "metadata.json"
            metadata = json.loads(metadata_path.read_text())
            self.assertEqual("20260630_existing-story-session", metadata["planning_session_id"])
            self.assertEqual(str(target_repo.resolve()), metadata["target_repo"])
            self.assertEqual("start", metadata["status"])
            target_artifact = target_repo / ".harness" / "sessions" / "20260630_existing-story-session" / "artifact.html"
            index_html_text = (coordinator / ".harness" / "sessions" / "epic-approval" / "index.html").read_text()
            self.assertIn("target-repo", index_html_text)
            self.assertIn("20260630_existing-story-session", index_html_text)
            self.assertIn(target_artifact.resolve().as_uri(), index_html_text)

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

    def test_implement_blocks_ready_story_without_linked_planning_session(self):
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
            metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")

            result = self.run_cli(cwd, "implement", "story-001", check=False)

            self.assertNotEqual(0, result.returncode)
            self.assertIn("has no linked repo-local planning session", result.stderr)

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
            story_2["planning_session_id"] = "child-session-id-b"
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
            self.assertIn("width: min(1440px, calc(100% - 56px));", html_text)
            self.assertIn("grid-template-columns: minmax(0, 1fr) minmax(300px, 360px);", html_text)
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

    def test_next_reports_start_transition_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            result = self.run_cli(cwd, "start", "req-login-timeout")
            created_line = next(line for line in result.stdout.splitlines() if line.startswith("created session: "))
            session_id = created_line.removeprefix("created session: ")

            result = self.run_cli(cwd, "next", session_id)

            self.assertIn(f"Session: {session_id}", result.stdout)
            self.assertIn("State: start", result.stdout)
            self.assertIn("Next action: transition to planning", result.stdout)
            self.assertIn("Blocked by: none", result.stdout)
            self.assertIn(f"- harness validate {session_id}", result.stdout)
            self.assertIn(f"- harness transition {session_id} planning", result.stdout)

    def test_next_reports_planning_blockers(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            start = self.run_cli(cwd, "start", "req-login-timeout")
            created_line = next(line for line in start.stdout.splitlines() if line.startswith("created session: "))
            session_id = created_line.removeprefix("created session: ")
            self.run_cli(cwd, "transition", session_id, "planning")

            result = self.run_cli(cwd, "next", session_id)

            self.assertIn("State: planning", result.stdout)
            self.assertIn("Blocked by:", result.stdout)
            self.assertIn("- Requirement Summary must be filled", result.stdout)
            self.assertIn("- Acceptance Criteria must be filled", result.stdout)
            self.assertIn("After resolving blockers, run:", result.stdout)
            self.assertIn(f"- harness approve-planning {session_id}", result.stdout)

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
            alpha = self.run_cli(cwd, "start", "alpha").stdout.splitlines()[0].removeprefix("created session: ")
            beta = self.run_cli(cwd, "start", "beta").stdout.splitlines()[0].removeprefix("created session: ")
            with sqlite3.connect(cwd / ".harness" / "harness.db") as conn:
                conn.execute("UPDATE sessions SET updated_at = ? WHERE session_id = ?", ("2026-01-01T00:00:00+00:00", alpha))
                conn.execute("UPDATE sessions SET updated_at = ? WHERE session_id = ?", ("2026-01-02T00:00:00+00:00", beta))

            result = self.run_cli(cwd, "list")

            lines = result.stdout.splitlines()
            self.assertEqual("session_id\tstate\tupdated_at\trecovery_attempts\tartifact", lines[0])
            self.assertTrue(lines[1].startswith(f"{beta}\tstart\t2026-01-02T00:00:00+00:00\t0\t"))
            self.assertTrue(lines[2].startswith(f"{alpha}\tstart\t2026-01-01T00:00:00+00:00\t0\t"))
            self.assertIn(f".harness/sessions/{beta}/artifact.md", lines[1])
            self.assertIn(f".harness/sessions/{alpha}/artifact.md", lines[2])

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

    def test_approve_planning_stops_background_annotation_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            self.run_cli(cwd, "start", "req-login-timeout")
            artifact = cwd / ".harness" / "sessions" / "req-login-timeout" / "artifact.md"
            session_id = artifact.resolve().parent.name
            text = artifact.read_text()
            text = text.replace("TBD", "Download Neraca as Excel", 1)
            text = text.replace("- [ ] TBD", "- [ ] Acceptance exists", 1)
            text = text.replace("- [ ] TBD", "- [ ] Validation exists", 1)
            text = text.replace("- [ ] TBD", "- [ ] Implementation task", 1)
            artifact.write_text(self.with_guidance(text))
            self.run_cli(cwd, "transition", "req-login-timeout", "planning")

            with mock.patch.object(self.harness_module, "stop_background_serve") as stop_background_serve:
                result = self.run_cli(cwd, "approve-planning", "req-login-timeout", "--by", "Liem")

            self.assertIn("planning approved by Liem", result.stdout)
            stop_background_serve.assert_called_once_with(session_id)

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
            session_id = self.harness_module.parse_frontmatter(artifact.read_text())[0]["session_id"]
            with sqlite3.connect(cwd / ".harness" / "harness.db") as conn:
                count = conn.execute("SELECT COUNT(*) FROM review_passes WHERE session_id = ?", (session_id,)).fetchone()[0]
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
            session_id = self.harness_module.parse_frontmatter(text)[0]["session_id"]
            with sqlite3.connect(cwd / ".harness" / "harness.db") as conn:
                row = conn.execute("SELECT description, resolved FROM required_fixes WHERE session_id = ?", (session_id,)).fetchone()
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

    def test_review_recovery_clears_review_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            artifact = self.enter_review(cwd)
            artifact.write_text(
                artifact.read_text()
                .replace("### AI Review\n\nTBD", "### AI Review\n\nNo blocking issues.")
                .replace("### Human Review\n\nTBD", "### Human Review\n\nLooks correct.")
            )
            self.run_cli(cwd, "approve-review", "req-login-timeout", "--by", "Liem")

            self.run_cli(cwd, "recover", "req-login-timeout", "--reason", "review item changed code")

            text = artifact.read_text()
            self.assertIn('review_approved: "false"', text)
            self.assertIn('review_approved_by: ""', text)
            self.assertIn("### Human Review\n\nTBD", text)
            with sqlite3.connect(cwd / ".harness" / "harness.db") as conn:
                count = conn.execute(
                    "SELECT COUNT(*) FROM approvals WHERE session_id = ? AND approval_type = ?",
                    ("req-login-timeout", "review"),
                ).fetchone()[0]
            self.assertEqual(0, count)

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

            self.assertRegex(result.stdout, r"Session history: \d{8}_req-login-timeout")
            self.assertIn("Transitions", result.stdout)
            self.assertIn("start -> planning success", result.stdout)
            self.assertIn("review -> needs-fix recovery reason: open review item: Add validation proof", result.stdout)
            self.assertIn("Approvals", result.stdout)
            self.assertIn("planning by Liem", result.stdout)
            self.assertNotIn("review by Liem", result.stdout)
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

    def test_quality_recovery_clears_stale_quality_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            artifact = self.enter_quality_check(cwd)
            self.complete_quality_check(cwd, artifact)

            self.run_cli(cwd, "recover", "req-login-timeout", "--reason", "quality check failed")

            text = artifact.read_text()
            self.assertIn("### Commands Run\n\nTBD", text)
            self.assertIn("### Proof\n\n- [ ] TBD", text)
            self.assertIn("### Manual Validation\n\nTBD", text)
            with sqlite3.connect(cwd / ".harness" / "harness.db") as conn:
                count = conn.execute(
                    "SELECT COUNT(*) FROM proofs WHERE session_id = ?",
                    ("req-login-timeout",),
                ).fetchone()[0]
            self.assertEqual(0, count)

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
            self.assertIn("choose a short kebab-case session title", text)
            self.assertIn("harness start <session-title>", text)
            self.assertIn("YYYYMMDD_<session-title>", text)
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
            self.assertIn("choose a short kebab-case session title", common_text)
            self.assertIn("harness start <session-title>", common_text)
            self.assertIn("YYYYMMDD_<session-title>", common_text)
            planning_text = (cwd / ".harness" / "agents" / "planning.md").read_text()
            self.assertIn("Read `.harness/project/index.md`", planning_text)
            self.assertIn("Use an interview loop during planning", planning_text)
            self.assertIn("gap between the user's requested behavior, the proposed plan, and the current codebase", planning_text)
            self.assertIn("Grilling Protocol", planning_text)
            self.assertIn(".agents/skills/grilling/SKILL.md", planning_text)
            self.assertIn("Stop asking once no open decisions remain", planning_text)
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
            self.assertIn("Bounded Worker Mode", implementation_text)
            self.assertIn("approved artifact as the execution contract", implementation_text)
            self.assertIn("Do not perform broad repo exploration", implementation_text)
            self.assertIn("return to planning with the exact missing file, symbol, behavior, or decision", implementation_text)
            review_text = (cwd / ".harness" / "agents" / "review.md").read_text()
            self.assertIn("review the implementation against the approved artifact", review_text)
            self.assertIn("the current diff", review_text)
            self.assertIn("artifact", review_text)
            self.assertIn("insufficient for review", review_text)
            quality_text = (cwd / ".harness" / "agents" / "quality-check.md").read_text()
            self.assertIn("execute the approved `## Validation Plan` as written", quality_text)
            self.assertIn("Do not invent additional validation scope", quality_text)
            self.assertIn("return to planning with the exact", quality_text)
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

    def test_update_refreshes_local_code_review_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")
            skill_file = cwd / ".agents" / "skills" / "code-review-expert" / "SKILL.md"
            skill_file.write_text("stale\n")

            result = self.run_cli(cwd, "update", "--skip-pull")

            self.assertIn("installed/refreshed local skills: code-review-expert", result.stdout)
            self.assertIn("grilling", result.stdout)
            self.assertIn("Code Review Expert", skill_file.read_text())
            self.assertEqual(
                skill_file.resolve(),
                (cwd / ".codex" / "skills" / "code-review-expert" / "SKILL.md").resolve(),
            )
            grilling_file = cwd / ".agents" / "skills" / "grilling" / "SKILL.md"
            self.assertIn("Interview me relentlessly", grilling_file.read_text())

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

    def test_generated_guardrails_are_loaded_from_source_docs(self):
        generated = self.harness_module.default_agents()
        self.assertEqual(
            (ROOT / ".harness" / "agents" / "implementation.md").read_text(),
            generated["implementation.md"],
        )

    def test_init_generates_guardrail_for_every_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.run_cli(cwd, "init")

            for state in self.harness_module.STATES:
                self.assertTrue((cwd / ".harness" / "agents" / f"{state}.md").exists(), state)

    def test_init_installs_local_code_review_skill_and_mirrors(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_cli(cwd, "init")

            skill_dir = cwd / ".agents" / "skills" / "code-review-expert"
            self.assertIn("installed local skills: code-review-expert", result.stdout)
            self.assertTrue((skill_dir / "SKILL.md").exists())
            self.assertTrue((skill_dir / "references" / "security-checklist.md").exists())
            for mirror in (".codex", ".claude", ".opencode"):
                mirror_path = cwd / mirror / "skills" / "code-review-expert"
                self.assertTrue(mirror_path.is_symlink(), mirror_path)
                self.assertEqual(skill_dir.resolve(), mirror_path.resolve())
            project_skill_path = cwd / "skills" / "code-review-expert"
            self.assertTrue(project_skill_path.is_symlink())
            self.assertEqual(skill_dir.resolve(), project_skill_path.resolve())

    def test_init_installs_local_grilling_skill_and_mirrors(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_cli(cwd, "init")

            skill_dir = cwd / ".agents" / "skills" / "grilling"
            self.assertIn("grilling", result.stdout)
            skill_text = (skill_dir / "SKILL.md").read_text()
            self.assertIn("name: grilling", skill_text)
            self.assertIn("Interview me relentlessly", skill_text)
            self.assertIn("mattpocock/skills", skill_text)
            for mirror in (".codex", ".claude", ".opencode"):
                mirror_path = cwd / mirror / "skills" / "grilling"
                self.assertTrue(mirror_path.is_symlink(), mirror_path)
                self.assertEqual(skill_dir.resolve(), mirror_path.resolve())
            project_skill_path = cwd / "skills" / "grilling"
            self.assertTrue(project_skill_path.is_symlink())
            self.assertEqual(skill_dir.resolve(), project_skill_path.resolve())

    def test_init_appends_to_existing_project_skills_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            existing_dir = cwd / "skills" / "existing-skill"
            existing_dir.mkdir(parents=True)
            existing_file = existing_dir / "SKILL.md"
            existing_file.write_text("existing\n")

            self.run_cli(cwd, "init")

            self.assertEqual("existing\n", existing_file.read_text())
            appended = cwd / "skills" / "code-review-expert"
            self.assertTrue(appended.is_symlink())
            self.assertEqual(
                (cwd / ".agents" / "skills" / "code-review-expert").resolve(),
                appended.resolve(),
            )

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
            self.assertIn("stable repo orientation", (project / "index.md").read_text())

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
            self.assertIn("Proof Expectations", (project / "validation.md").read_text())
            self.assertIn("command output summaries", (project / "validation.md").read_text())
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
            session_id = artifact.resolve().parent.name
            self.complete_quality_check(cwd, artifact)
            self.run_cli(cwd, "transition", "req-login-timeout", "approval")

            with mock.patch.object(self.harness_module, "stop_background_serve") as stop_background_serve:
                result = self.run_cli(cwd, "approve-quality", "req-login-timeout", "--by", "Liem")
                done = self.run_cli(cwd, "transition", "req-login-timeout", "done")

            self.assertIn("quality approved by Liem", result.stdout)
            text = artifact.read_text()
            self.assertIn('quality_approved: "true"', text)
            self.assertIn('quality_approved_by: "Liem"', text)
            self.assertIn("## Final Approval\n\nApproved by Liem", text)
            self.assertIn("transitioned: approval -> done", done.stdout)
            self.assertEqual(
                [mock.call(session_id), mock.call(session_id)],
                stop_background_serve.call_args_list,
            )

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
            session_id = self.harness_module.parse_frontmatter(artifact.read_text())[0]["session_id"]
            with sqlite3.connect(cwd / ".harness" / "harness.db") as conn:
                state = conn.execute("SELECT state FROM sessions WHERE session_id = ?", (session_id,)).fetchone()[0]
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
            session_id = self.harness_module.parse_frontmatter(artifact.read_text())[0]["session_id"]
            with sqlite3.connect(cwd / ".harness" / "harness.db") as conn:
                row = conn.execute("SELECT path FROM proofs WHERE session_id = ?", (session_id,)).fetchone()
            self.assertTrue(row[0].endswith("proof/result.txt"))

    def test_install_script_clones_and_symlinks_harness(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = self.make_installer_source_fixture(tmp)
            home = tmp / "home"
            install_dir = home / ".workflow-project"
            bin_dir = home / ".local" / "bin"
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["HARNESS_REPO_URL"] = str(source)
            env["HARNESS_INSTALL_DIR"] = str(install_dir)
            env["HARNESS_BIN_DIR"] = str(bin_dir)
            result = subprocess.run(
                ["bash", str(INSTALLER)],
                cwd=tmp,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            if result.returncode != 0:
                self.fail(f"install.sh failed\nstdout={result.stdout}\nstderr={result.stderr}")

            harness_link = bin_dir / "harness"
            self.assertTrue((install_dir / ".git").exists())
            self.assertTrue(harness_link.is_symlink())
            self.assertEqual((install_dir / "bin" / "harness").resolve(), harness_link.resolve())
            self.assertIn("Installed harness.", result.stdout)
            self.assertIn("start your-session-id", result.stdout)

            rerun = subprocess.run(
                ["bash", str(INSTALLER)],
                cwd=tmp,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            if rerun.returncode != 0:
                self.fail(f"install.sh rerun failed\nstdout={rerun.stdout}\nstderr={rerun.stderr}")
            self.assertIn("updating existing harness source", rerun.stdout)

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


    # ------------------------------------------------------------------
    # Inline annotations
    # ------------------------------------------------------------------

    def start_session(self, cwd: Path, title: str = "annotate-me") -> str:
        self.run_cli(cwd, "init")
        result = self.run_cli(cwd, "start", title)
        created = next(
            line for line in result.stdout.splitlines() if line.startswith("created session: ")
        )
        return created.removeprefix("created session: ").strip()

    def test_slugify_is_deterministic_and_safe(self):
        slugify = self.harness_module.slugify
        self.assertEqual(slugify("Requirement Summary"), "requirement-summary")
        self.assertEqual(slugify("Requirement Summary"), slugify("Requirement Summary"))
        self.assertEqual(slugify("<code>Review</code> &amp; Fixes"), "review-fixes")
        self.assertEqual(slugify("!!!"), "section")

    def test_section_anchors_rendered_in_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            session_id = self.start_session(cwd)
            self.run_cli(cwd, "status", session_id)
            html_path = cwd / ".harness" / "sessions" / session_id / "artifact.html"
            html = html_path.read_text()
            self.assertIn('data-section="requirement-summary"', html)
            self.assertIn('id="section-requirement-summary"', html)

    def test_annotation_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            session_id = self.start_session(cwd)
            old_cwd = Path.cwd()
            try:
                os.chdir(cwd)
                created = self.harness_module.add_annotation(
                    session_id,
                    {
                        "quote": "important detail",
                        "comment": "please expand",
                        "section": "requirement-summary",
                        "prefix": "some ",
                        "suffix": " here",
                    },
                )
                stored = self.harness_module.load_annotations(session_id)
            finally:
                os.chdir(old_cwd)
            self.assertEqual(len(stored), 1)
            self.assertEqual(stored[0]["id"], created["id"])
            self.assertEqual(stored[0]["quote"], "important detail")
            self.assertEqual(stored[0]["status"], "open")
            path = cwd / ".harness" / "sessions" / session_id / "annotations.json"
            self.assertTrue(path.exists())

    def test_served_annotation_page_omits_addressed_annotations(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            session_id = self.start_session(cwd)
            old_cwd = Path.cwd()
            try:
                os.chdir(cwd)
                open_annotation = self.harness_module.add_annotation(
                    session_id,
                    {
                        "quote": "open-only quote",
                        "comment": "still needs work",
                        "section": "requirement-summary",
                    },
                )
                addressed_annotation = self.harness_module.add_annotation(
                    session_id,
                    {
                        "quote": "addressed-only quote",
                        "comment": "already fixed",
                        "section": "requirement-summary",
                    },
                )
                self.harness_module.update_annotation(
                    session_id, addressed_annotation["id"], {"status": "addressed"}
                )
                page = self.harness_module.build_annotation_page(session_id)
                stored = self.harness_module.load_annotations(session_id)
            finally:
                os.chdir(old_cwd)

            self.assertEqual(len(stored), 2)
            self.assertIn(open_annotation["id"], page)
            self.assertIn("open-only quote", page)
            self.assertIn("mark.hx-mark { background: #d8f5d0; color: #14532d;", page)
            self.assertNotIn(addressed_annotation["id"], page)
            self.assertNotIn("addressed-only quote", page)

    def test_annotation_page_keeps_artifact_proportional_with_comments_panel(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            session_id = self.start_session(cwd)
            old_cwd = Path.cwd()
            try:
                os.chdir(cwd)
                page = self.harness_module.build_annotation_page(session_id)
            finally:
                os.chdir(old_cwd)

            self.assertIn("--hx-panel-width: clamp(300px, 17vw, 360px);", page)
            self.assertIn("body.hx-has-panel { padding-right: var(--hx-panel-width); }", page)
            self.assertIn("width: min(1920px, calc(100% - var(--hx-page-gap) - var(--hx-page-gap)));", page)
            self.assertNotIn("width: min(1100px, calc(100% - 380px)); margin-left: 24px;", page)

    def test_add_annotation_requires_quote_and_comment(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            session_id = self.start_session(cwd)
            old_cwd = Path.cwd()
            try:
                os.chdir(cwd)
                with self.assertRaises(ValueError):
                    self.harness_module.add_annotation(session_id, {"quote": "x", "comment": ""})
            finally:
                os.chdir(old_cwd)

    def test_annotations_command_resolves_and_marks_addressed(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            session_id = self.start_session(cwd)
            artifact = cwd / ".harness" / "sessions" / session_id / "artifact.md"
            artifact.write_text(
                artifact.read_text().replace(
                    "## Requirement Summary\n\nTBD",
                    "## Requirement Summary\n\nThe endpoint must validate the token first.",
                )
            )
            old_cwd = Path.cwd()
            try:
                os.chdir(cwd)
                created = self.harness_module.add_annotation(
                    session_id,
                    {
                        "quote": "validate the token",
                        "comment": "which store?",
                        "section": "requirement-summary",
                    },
                )
            finally:
                os.chdir(old_cwd)
            annotation_id = created["id"]

            listed = self.run_cli(cwd, "annotations", session_id)
            self.assertIn(annotation_id, listed.stdout)
            self.assertIn("artifact.md:", listed.stdout)
            self.assertIn("which store?", listed.stdout)

            self.run_cli(cwd, "annotations", session_id, "--resolve", annotation_id)

            after = self.run_cli(cwd, "annotations", session_id)
            self.assertIn("No open annotations.", after.stdout)
            with_all = self.run_cli(cwd, "annotations", session_id, "--all")
            self.assertIn(annotation_id, with_all.stdout)
            self.assertIn("addressed", with_all.stdout)

    def test_annotations_resolve_refreshes_html_and_auto_serves(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            session_id = self.start_session(cwd)
            self.run_cli(cwd, "transition", session_id, "planning")
            artifact = cwd / ".harness" / "sessions" / session_id / "artifact.md"
            html_path = artifact.with_suffix(".html")
            artifact.write_text(self.with_guidance(self.fill_planning(artifact.read_text())))
            old_cwd = Path.cwd()
            try:
                os.chdir(cwd)
                created = self.harness_module.add_annotation(
                    session_id,
                    {
                        "quote": "Ship the feature.",
                        "comment": "make this specific",
                        "section": "requirement-summary",
                    },
                )
            finally:
                os.chdir(old_cwd)
            artifact.write_text(artifact.read_text().replace("Ship the feature.", "Ship the token refresh feature."))

            with mock.patch.object(self.harness_module, "start_background_serve", return_value={
                "pid": 123,
                "port": 456,
                "url": "http://127.0.0.1:456/",
                "started_at": "2026-07-03T00:00:00Z",
            }) as start_background_serve, \
                 mock.patch.object(self.harness_module, "_open_browser") as open_browser:
                result = self.run_cli(
                    cwd,
                    "annotations",
                    session_id,
                    "--resolve",
                    created["id"],
                    env={"HARNESS_AUTO_SERVE": "1"},
                )

            self.assertIn(f"marked addressed: {created['id']}", result.stdout)
            self.assertIn("Ship the token refresh feature.", html_path.read_text())
            start_background_serve.assert_called_once_with(session_id)
            open_browser.assert_called_once_with("http://127.0.0.1:456/")

    def test_annotations_resolve_serves_after_batch_is_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            session_id = self.start_session(cwd)
            self.run_cli(cwd, "transition", session_id, "planning")
            artifact = cwd / ".harness" / "sessions" / session_id / "artifact.md"
            html_path = artifact.with_suffix(".html")
            artifact.write_text(self.with_guidance(self.fill_planning(artifact.read_text())))
            html_path.write_text("stale html")
            old_cwd = Path.cwd()
            try:
                os.chdir(cwd)
                first = self.harness_module.add_annotation(
                    session_id,
                    {
                        "quote": "Ship the feature.",
                        "comment": "make this specific",
                        "section": "requirement-summary",
                    },
                )
                second = self.harness_module.add_annotation(
                    session_id,
                    {
                        "quote": "Acceptance exists",
                        "comment": "include the edge case",
                        "section": "acceptance-criteria",
                    },
                )
            finally:
                os.chdir(old_cwd)

            with mock.patch.object(self.harness_module, "start_background_serve", return_value={
                "pid": 123,
                "port": 456,
                "url": "http://127.0.0.1:456/",
                "started_at": "2026-07-03T00:00:00Z",
            }) as start_background_serve, \
                 mock.patch.object(self.harness_module, "_open_browser") as open_browser:
                first_result = self.run_cli(
                    cwd,
                    "annotations",
                    session_id,
                    "--resolve",
                    first["id"],
                    env={"HARNESS_AUTO_SERVE": "1"},
                )
                html_after_first_resolve = html_path.read_text()
                second_result = self.run_cli(
                    cwd,
                    "annotations",
                    session_id,
                    "--resolve",
                    second["id"],
                    env={"HARNESS_AUTO_SERVE": "1"},
                )

            self.assertIn("1 open annotation(s) remain", first_result.stdout)
            self.assertEqual("stale html", html_after_first_resolve)
            self.assertIn(f"marked addressed: {second['id']}", second_result.stdout)
            self.assertIn("Ship the feature.", html_path.read_text())
            start_background_serve.assert_called_once_with(session_id)
            open_browser.assert_called_once_with("http://127.0.0.1:456/")

    def test_annotations_command_flags_stale_quote(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            session_id = self.start_session(cwd)
            old_cwd = Path.cwd()
            try:
                os.chdir(cwd)
                self.harness_module.add_annotation(
                    session_id,
                    {
                        "quote": "text that is not present anywhere",
                        "comment": "check stale",
                        "section": "requirement-summary",
                    },
                )
            finally:
                os.chdir(old_cwd)
            listed = self.run_cli(cwd, "annotations", session_id)
            self.assertIn("stale", listed.stdout)

    def test_annotations_do_not_touch_state_machine(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            session_id = self.start_session(cwd)
            before = self.run_cli(cwd, "status", session_id).stdout
            old_cwd = Path.cwd()
            try:
                os.chdir(cwd)
                created = self.harness_module.add_annotation(
                    session_id,
                    {"quote": "TBD", "comment": "note", "section": "requirement-summary"},
                )
                self.harness_module.update_annotation(
                    session_id, created["id"], {"status": "addressed"}
                )
            finally:
                os.chdir(old_cwd)
            after = self.run_cli(cwd, "status", session_id).stdout
            self.assertIn("State: start", before)
            self.assertIn("State: start", after)
            # No annotations table should have been created in the state store.
            db = sqlite3.connect(cwd / ".harness" / "harness.db")
            try:
                tables = {
                    row[0]
                    for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
                }
            finally:
                db.close()
            self.assertNotIn("annotations", tables)

    def test_serve_handler_get_post_shutdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            session_id = self.start_session(cwd)
            old_cwd = Path.cwd()
            try:
                os.chdir(cwd)
                from http.server import ThreadingHTTPServer
                import threading
                import urllib.request

                server = ThreadingHTTPServer(
                    ("127.0.0.1", 0), self.harness_module.make_annotation_handler(session_id)
                )
                port = server.server_address[1]
                worker = threading.Thread(target=server.serve_forever)
                worker.start()
                base = f"http://127.0.0.1:{port}"
                try:
                    page = urllib.request.urlopen(base + "/").read().decode()
                    self.assertIn("hx-toolbar", page)

                    req = urllib.request.Request(
                        base + "/annotations",
                        data=json.dumps(
                            {
                                "quote": "TBD",
                                "comment": "served",
                                "section": "requirement-summary",
                            }
                        ).encode(),
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    created = json.load(urllib.request.urlopen(req))
                    self.assertEqual(created["status"], "open")

                    shutdown = urllib.request.Request(
                        base + "/shutdown", data=b"{}", method="POST"
                    )
                    urllib.request.urlopen(shutdown)
                finally:
                    worker.join(timeout=5)
                    server.server_close()
                self.assertFalse(worker.is_alive())
                self.assertEqual(len(self.harness_module.load_annotations(session_id)), 1)
            finally:
                os.chdir(old_cwd)


    def test_running_serve_detects_dead_pid(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            session_id = self.start_session(cwd)
            old_cwd = Path.cwd()
            try:
                os.chdir(cwd)
                state_path = self.harness_module.serve_state_path(session_id)
                state_path.write_text(json.dumps({"pid": 2147480000, "port": 1, "url": "http://127.0.0.1:1/"}))
                self.assertIsNone(self.harness_module.running_serve(session_id))
                self.assertFalse(state_path.exists())
            finally:
                os.chdir(old_cwd)

    def test_auto_serve_respects_env_optout(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            session_id = self.start_session(cwd)
            artifact = cwd / ".harness" / "sessions" / session_id / "artifact.md"
            artifact.write_text(self.with_guidance(self.fill_planning(artifact.read_text())))
            self.run_cli(cwd, "transition", session_id, "planning")
            # run_cli sets HARNESS_AUTO_SERVE=0, so a passing planning validate must not fork/serve.
            result = self.run_cli(cwd, "validate", session_id)
            self.assertIn("valid", result.stdout)
            self.assertFalse((cwd / ".harness" / "sessions" / session_id / ".serve.json").exists())

    def test_auto_serve_defaults_enabled_when_env_unset(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            session_id = self.start_session(cwd)
            artifact = cwd / ".harness" / "sessions" / session_id / "artifact.md"
            artifact.write_text(self.with_guidance(self.fill_planning(artifact.read_text())))
            self.run_cli(cwd, "transition", session_id, "planning")
            old_cwd = Path.cwd()
            try:
                os.chdir(cwd)
                with mock.patch.dict(os.environ, {}, clear=True), \
                     mock.patch.object(self.harness_module, "start_background_serve", return_value={
                         "pid": 123,
                         "port": 456,
                         "url": "http://127.0.0.1:456/",
                         "started_at": "2026-07-03T00:00:00Z",
                     }) as start_background_serve, \
                     mock.patch.object(self.harness_module, "_open_browser") as open_browser:
                    self.harness_module.maybe_auto_serve_planning(session_id)
            finally:
                os.chdir(old_cwd)
            start_background_serve.assert_called_once_with(session_id)
            open_browser.assert_called_once_with("http://127.0.0.1:456/")

    def test_auto_serve_enabled_recognizes_false_values(self):
        for value in ("0", "false", "no", "off", ""):
            with self.subTest(value=value):
                with mock.patch.dict(os.environ, {"HARNESS_AUTO_SERVE": value}):
                    self.assertFalse(self.harness_module.auto_serve_enabled())

        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertTrue(self.harness_module.auto_serve_enabled())

    def test_start_background_serve_round_trip(self):
        if not hasattr(os, "fork"):
            self.skipTest("os.fork unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            session_id = self.start_session(cwd)
            old_cwd = Path.cwd()
            import urllib.request
            import time

            state = None
            try:
                os.chdir(cwd)
                state = self.harness_module.start_background_serve(session_id)
                self.assertIsNotNone(state)
                base = state["url"].rstrip("/")
                # server responds
                deadline = time.time() + 5
                page = None
                while time.time() < deadline:
                    try:
                        page = urllib.request.urlopen(base + "/").read().decode()
                        break
                    except Exception:
                        time.sleep(0.05)
                self.assertIsNotNone(page)
                self.assertIn("hx-toolbar", page)
                # dedup: running_serve reports the same live process
                self.assertEqual(self.harness_module.running_serve(session_id)["pid"], state["pid"])
                # Complete button -> shutdown
                urllib.request.urlopen(urllib.request.Request(base + "/shutdown", data=b"{}", method="POST"))
                os.waitpid(state["pid"], 0)
                self.assertFalse((cwd / ".harness" / "sessions" / session_id / ".serve.json").exists())
                state = None
            finally:
                if state and state.get("pid"):
                    try:
                        os.kill(state["pid"], 9)
                        os.waitpid(state["pid"], 0)
                    except OSError:
                        pass
                os.chdir(old_cwd)

    def test_stop_background_serve_round_trip(self):
        if not hasattr(os, "fork"):
            self.skipTest("os.fork unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            session_id = self.start_session(cwd)
            old_cwd = Path.cwd()
            import urllib.request
            import time

            state = None
            try:
                os.chdir(cwd)
                state = self.harness_module.start_background_serve(session_id)
                self.assertIsNotNone(state)
                base = state["url"].rstrip("/")
                deadline = time.time() + 5
                page = None
                while time.time() < deadline:
                    try:
                        page = urllib.request.urlopen(base + "/").read().decode()
                        break
                    except Exception:
                        time.sleep(0.05)
                self.assertIsNotNone(page)

                self.assertTrue(self.harness_module.stop_background_serve(session_id))
                self.assertIsNone(self.harness_module.running_serve(session_id))
                self.assertFalse((cwd / ".harness" / "sessions" / session_id / ".serve.json").exists())
                state = None
            finally:
                if state and state.get("pid"):
                    try:
                        os.kill(state["pid"], 9)
                        os.waitpid(state["pid"], 0)
                    except OSError:
                        pass
                os.chdir(old_cwd)

    def fill_planning(self, text: str) -> str:
        text = text.replace("## Requirement Summary\n\nTBD", "## Requirement Summary\n\nShip the feature.")
        text = text.replace("- [ ] TBD", "- [x] Acceptance exists", 1)
        text = text.replace("- [ ] TBD", "- [x] Run validation", 1)
        text = text.replace("- [ ] TBD", "- [x] Implementation complete", 1)
        return text


class TestInstallUserSubagents(unittest.TestCase):
    """Tests for install_user_subagents() and its integration with init/update."""

    def _run_harness(self, cwd: Path, args: list[str], fake_home: Path, extra_env: Optional[dict] = None) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["HARNESS_SKIP_LANGUAGE_SKILLS"] = "1"
        env["HARNESS_AUTO_SERVE"] = "0"
        env["HOME"] = str(fake_home)
        env.pop("HARNESS_SKIP_USER_SUBAGENTS", None)
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=str(cwd),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

    def test_init_installs_user_subagents(self):
        """init creates all six sub-agent files in a fresh HOME."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fake_home = tmp / "home"
            fake_home.mkdir()
            project = tmp / "project"
            project.mkdir()
            result = self._run_harness(project, ["init"], fake_home)
            self.assertEqual(result.returncode, 0, f"init failed: {result.stderr}")

            claude_agents = fake_home / ".claude" / "agents"
            codex_agents = fake_home / ".codex" / "agents"

            for name, marker in [
                ("code-explorer.md", "name: code-explorer"),
                ("implementer.md", "name: implementer"),
                ("code-reviewer.md", "name: code-reviewer"),
            ]:
                path = claude_agents / name
                self.assertTrue(path.exists(), f"missing {path}")
                self.assertIn(marker, path.read_text())

            for name, marker in [
                ("code-explorer.toml", 'model = "gpt-5.6-luna"\nmodel_reasoning_effort = "high"'),
                ("implementer.toml", 'model = "gpt-5.6-luna"\nmodel_reasoning_effort = "high"'),
                ("code-reviewer.toml", 'model = "gpt-5.6-sol"\nmodel_reasoning_effort = "medium"'),
            ]:
                path = codex_agents / name
                self.assertTrue(path.exists(), f"missing {path}")
                self.assertIn(marker, path.read_text())

            explorer_config = (codex_agents / "code-explorer.toml").read_text()
            implementer_config = (codex_agents / "implementer.toml").read_text()
            reviewer_config = (codex_agents / "code-reviewer.toml").read_text()
            for config in [explorer_config, implementer_config]:
                self.assertIn('model = "gpt-5.6-luna"', config)
                self.assertIn('model_reasoning_effort = "high"', config)
            self.assertIn('model_reasoning_effort = "low"', reviewer_config)

            self.assertIn("installed/refreshed user sub-agents:", result.stdout)

    def test_init_refreshes_existing_user_subagents(self):
        """init refreshes existing harness-managed files and preserves unrelated agents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fake_home = tmp / "home"
            fake_home.mkdir()
            claude_agents = fake_home / ".claude" / "agents"
            claude_agents.mkdir(parents=True)
            sentinel_content = "STALE_HARNESS_MANAGED_AGENT"
            (claude_agents / "implementer.md").write_text(sentinel_content)
            custom_agent = claude_agents / "my-custom-agent.md"
            custom_agent.write_text("CUSTOM_AGENT")

            project = tmp / "project"
            project.mkdir()
            result = self._run_harness(project, ["init"], fake_home)
            self.assertEqual(result.returncode, 0, f"init failed: {result.stderr}")

            self.assertNotEqual((claude_agents / "implementer.md").read_text(), sentinel_content)
            self.assertIn("name: implementer", (claude_agents / "implementer.md").read_text())
            self.assertEqual(custom_agent.read_text(), "CUSTOM_AGENT")

            # Other five files created
            codex_agents = fake_home / ".codex" / "agents"
            for name in ["code-explorer.md", "code-reviewer.md"]:
                self.assertTrue((claude_agents / name).exists(), f"missing claude/{name}")
            for name in ["code-explorer.toml", "implementer.toml", "code-reviewer.toml"]:
                self.assertTrue((codex_agents / name).exists(), f"missing codex/{name}")

    def test_update_refreshes_user_subagents(self):
        """harness update --skip-pull refreshes stale managed files and creates missing ones."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fake_home = tmp / "home"
            fake_home.mkdir()
            project = tmp / "project"
            project.mkdir()
            # init first so .harness dir exists (update needs it)
            init_result = self._run_harness(
                project, ["init"], fake_home,
                extra_env={"HARNESS_SKIP_USER_SUBAGENTS": "1"},
            )
            self.assertEqual(init_result.returncode, 0, f"init failed: {init_result.stderr}")
            claude_agents = fake_home / ".claude" / "agents"
            codex_agents = fake_home / ".codex" / "agents"
            claude_agents.mkdir(parents=True)
            codex_agents.mkdir(parents=True)
            (claude_agents / "code-reviewer.md").write_text("STALE_CLAUDE_AGENT")
            (codex_agents / "implementer.toml").write_text("STALE_CODEX_AGENT")
            custom_agent = codex_agents / "my-custom-agent.toml"
            custom_agent.write_text("CUSTOM_AGENT")

            update_result = self._run_harness(project, ["update", "--skip-pull"], fake_home)
            self.assertEqual(update_result.returncode, 0, f"update failed: {update_result.stderr}")

            for name in ["code-explorer.md", "implementer.md", "code-reviewer.md"]:
                self.assertTrue((claude_agents / name).exists(), f"missing claude/{name}")
            for name in ["code-explorer.toml", "implementer.toml", "code-reviewer.toml"]:
                self.assertTrue((codex_agents / name).exists(), f"missing codex/{name}")
            self.assertIn("name: code-reviewer", (claude_agents / "code-reviewer.md").read_text())
            self.assertIn('model = "gpt-5.6-terra"', (codex_agents / "implementer.toml").read_text())
            self.assertEqual(custom_agent.read_text(), "CUSTOM_AGENT")
            self.assertIn("installed/refreshed user sub-agents:", update_result.stdout)

    def test_init_replaces_managed_symlink_without_overwriting_target(self):
        """Refresh replaces a managed symlink entry instead of following its target."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fake_home = tmp / "home"
            codex_agents = fake_home / ".codex" / "agents"
            codex_agents.mkdir(parents=True)
            external_target = tmp / "external-agent.toml"
            external_target.write_text("DO_NOT_OVERWRITE")
            managed_agent = codex_agents / "code-explorer.toml"
            managed_agent.symlink_to(external_target)

            project = tmp / "project"
            project.mkdir()
            result = self._run_harness(project, ["init"], fake_home)
            self.assertEqual(result.returncode, 0, f"init failed: {result.stderr}")

            self.assertEqual(external_target.read_text(), "DO_NOT_OVERWRITE")
            self.assertFalse(managed_agent.is_symlink())
            self.assertIn('model = "gpt-5.6-terra"', managed_agent.read_text())

    def test_skip_user_subagents_env_gate(self):
        """HARNESS_SKIP_USER_SUBAGENTS=1 prevents any sub-agent files from being created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fake_home = tmp / "home"
            fake_home.mkdir()
            project = tmp / "project"
            project.mkdir()
            result = self._run_harness(
                project, ["init"], fake_home,
                extra_env={"HARNESS_SKIP_USER_SUBAGENTS": "1"},
            )
            self.assertEqual(result.returncode, 0, f"init failed: {result.stderr}")

            claude_agents = fake_home / ".claude" / "agents"
            codex_agents = fake_home / ".codex" / "agents"
            for name in ["code-explorer.md", "implementer.md", "code-reviewer.md"]:
                self.assertFalse((claude_agents / name).exists(), f"should not exist: claude/{name}")
            for name in ["code-explorer.toml", "implementer.toml", "code-reviewer.toml"]:
                self.assertFalse((codex_agents / name).exists(), f"should not exist: codex/{name}")


if __name__ == "__main__":
    unittest.main()
