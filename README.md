# Workflow Project Harness

Local harness orchestrator for agent-driven engineering workflows.

Model:

- Agent calls the CLI.
- CLI manages local SQLite state, session artifacts, and transition gates.
- SQLite is canonical for orchestration state.
- Markdown remains the human-readable agent artifact.

## Install

From this repo:

```bash
chmod +x bin/harness
```

Optional shell path:

```bash
export PATH="$PWD/bin:$PATH"
```

From another project, clone or add this repo as a tool source, then run the CLI with an absolute path:

```bash
/path/to/workflow-project/bin/harness init
```

You can also symlink it:

```bash
ln -sf /path/to/workflow-project/bin/harness /usr/local/bin/harness
```

## Usage

Initialize harness files:

```bash
bin/harness init
```

This creates `.harness/harness.db`, templates, guardrails, and project map files. The SQLite DB is local-only and ignored by git.

Create a session:

```bash
bin/harness start req-login-timeout
```

Check status and guardrails:

```bash
bin/harness status req-login-timeout
```

Validate the current state:

```bash
bin/harness validate req-login-timeout
```

Before editing product code, verify the edit gate:

```bash
bin/harness preflight-edit req-login-timeout
```

This exits non-zero unless the session is in `implementation` or `needs-fix` and the implementation gate requirements are satisfied.

Move state:

```bash
bin/harness transition req-login-timeout planning
bin/harness approve-planning req-login-timeout --by "Liem"
bin/harness transition req-login-timeout implementation
```

`planning -> implementation` requires explicit planning approval. Agents must not run `approve-planning` unless the user explicitly approves the plan.

`approve-planning` marks `## Acceptance Criteria` items checked as requirement approval, then locks a hash of Requirement Summary, Acceptance Criteria, and Validation Plan. If those planning sections change after approval, implementation/edit gates block until planning is approved again. Validation Plan and Implementation Checklist remain execution checklists; checking implementation items during implementation does not invalidate planning approval.

After implementation, move to review and stop for human review:

```bash
bin/harness transition req-login-timeout review
bin/harness record-review req-login-timeout --file review.md
bin/harness approve-review req-login-timeout --by "Liem"
bin/harness transition req-login-timeout quality-check
```

`review -> quality-check` requires explicit human review approval. Agents must not run `approve-review` unless the user explicitly approves the review.

In `review`, agents must persist AI review output with `harness record-review` before responding. A chat-only review is incomplete. AI findings are advisory until the human decides. Use `--required-fix` only for human-selected fixes that must block `review -> quality-check`.

During `implementation`, every item in `## Implementation Checklist` must be checked before review. If product files changed while checklist items remain unchecked, `harness status` and `harness validate` report the missing checklist work.

Implementation must not run quality validation. If `## Quality Check` commands/proof/manual validation are recorded before the session reaches `quality-check`, `harness status` and `harness validate` report a phase violation.

Inside `quality-check`, the agent must execute the artifact `## Validation Plan`, check off completed validation items, record commands/results under `## Quality Check > Commands Run`, and attach proof with `harness attach-proof`. `harness status` and `harness validate` report missing quality evidence until a checked proof link resolves to a file under the session `proof/` directory.

Quality proof policy is configured in `.harness/harness.yml`:

```yaml
quality_gate:
  required_proof: auto
```

Supported values:

- `auto`: infer backend/frontend expectations from the validation plan and project map.
- `backend`: require a curl command and sample response/status.
- `frontend`: require screenshot proof and view/browser validation notes.
- `both`: require backend and frontend proof.
- `manual`: require only generic commands/results and attached proof.

Attach proof:

```bash
bin/harness attach-proof req-login-timeout ./proof-output.txt
```

Check local harness integrity:

```bash
bin/harness doctor
```

Migrate existing Markdown-only sessions into SQLite:

```bash
bin/harness migrate-sqlite
```

If SQLite and Markdown frontmatter disagree, SQLite is canonical. `doctor` reports mirror mismatches.

## Upgrade Existing Projects

If a project already ran an older harness version, create the local SQLite DB, import existing sessions, and refresh guardrails:

```bash
harness init
harness migrate-sqlite
harness sync-guardrails --force
harness doctor
```

`harness init` does not overwrite existing non-empty templates or project maps. New sessions created from legacy templates automatically strip old Linear metadata fields.

Use `sync-guardrails --force` after CLI upgrades. It overwrites only the agent guardrail files and root `AGENTS.md`.

Legacy alias:

```bash
harness upgrade-guardrails
```

## Project Map

Project maps give agents a compact repo orientation before planning. They are not authority; current code always wins and agents must verify relevant facts by repo search.

Create missing map files:

```bash
harness init-project-map
```

This creates:

```text
.harness/project/
  overview.md
  architecture.md
  conventions.md
  validation.md
  risks.md
  index.md
```

Refresh the bundled project-map templates:

```bash
harness sync-project-map --force
```

This overwrites `.harness/project/*.md` templates only. It does not touch session artifacts under `.harness/sessions/`.

## Agent Flow

Tell an agent the session id. The agent should:

1. Read `AGENTS.md`.
2. Run `bin/harness status <session-id>`.
3. Read `.harness/agents/common.md`.
4. Read `.harness/project/index.md` when present.
5. Read the state guardrail printed by status.
6. Run `bin/harness preflight-edit <session-id>` before product code edits.
7. Work within that state only.

## Test

Run:

```bash
python3 -m unittest discover -s tests
```
