# Harness Orchestrator Implementation Plan

## Summary

Build a local harness orchestration system where the agent operates the workflow, the CLI enforces deterministic state transitions, Markdown artifacts remain canonical, and Linear mirrors state using credentials loaded from `.env`.

Target model:

- Agent calls the CLI.
- CLI creates and validates harness sessions.
- Markdown stores the durable plan, checklist, status, and proof links.
- Linear stores external visibility only.
- `.env` stores Linear credentials and optional default Linear config.

## Goals

- Create a repeatable workflow for requirement planning, implementation, review, quality check, and completion.
- Keep all canonical requirement and validation detail in repo-local Markdown artifacts.
- Use Linear as a state mirror and collaboration surface, not as the source of truth.
- Make state transitions explicit and guard them with required artifact content.
- Keep Linear API secrets out of paths, Markdown, logs, and proof files.

## Non-Goals

- Do not make the CLI spawn Codex, Cursor, or other agents in v0.
- Do not require Linear for local-only harness sessions.
- Do not store canonical artifacts in Linear.
- Do not introduce a database until cross-session search, analytics, or dashboards become necessary.
- Do not encode Linear API tokens in session folder names or artifacts.

## Architecture

### Agent

The agent is the operator. It performs exploratory and fuzzy work:

- asks ambiguity questions during planning
- explores the repo
- writes acceptance criteria
- implements code and tests
- runs validation
- interprets failures
- updates artifact sections and checklist items

### CLI

The CLI is the deterministic state enforcer. It handles:

- project initialization
- session creation
- template instantiation
- status reads and transitions
- transition validation
- proof attachment
- optional Linear sync

The CLI must fail with actionable messages when required artifact sections or proof are missing.

### Markdown Artifact

The Markdown artifact is canonical. It owns:

- current state
- Linear issue linkage
- acceptance criteria
- validation plan
- implementation checklist
- review checklist
- quality-check proof
- final completion evidence

### Linear

Linear is an external state mirror. It may store:

- mirrored workflow state
- transition comments
- proof summaries
- links or paths to local artifacts when useful

Linear must never replace the Markdown artifact as the source of truth.

### `.env`

Linear config is read from project `.env`, global `~/.config/harness/.env`, or process environment variables.

Project `.env` is an optional local override:

```env
LINEAR_API_KEY=
LINEAR_TEAM_ID=
LINEAR_PROJECT_ID=
```

Rules:

- `.env` must be gitignored.
- `.env.example` may be committed with placeholders.
- Global `~/.config/harness/.env` is recommended for shared personal credentials.
- `LINEAR_API_KEY` must never be written to artifacts, logs, proof files, or folder names.
- Missing `.env` must not block local-only harness usage.

## Repository Structure

```text
.harness/
  harness.yml
  agents/
    common.md
    start.md
    planning.md
    implementation.md
    review.md
    quality-check.md
    done.md
  templates/
    session.md
  sessions/
    <session-id>/
      artifact.md
      proof/
  plans/
    harness-orchestrator-implementation.md
.env.example
AGENTS.md
bin/
  harness
```

Session IDs are safe local identifiers. Example:

```text
.harness/sessions/req-login-timeout/artifact.md
```

Linear issue keys are non-secret and should live in artifact metadata:

```yaml
linear_issue_key: WF-123
linear_issue_url: https://linear.app/example/issue/WF-123/example
```

## State Machine

```text
start -> planning -> implementation -> review -> quality-check -> done
                         ^                 |
                         |                 v
                         +----------- needs-fix
```

States:

- `start`: session created, artifact initialized
- `planning`: acceptance criteria and validation plan are being written
- `implementation`: code and tests are being changed
- `review`: AI and human review findings are collected
- `needs-fix`: review or validation found required fixes
- `quality-check`: validation plan is executed and proof is attached
- `done`: all mandatory checklist items and proof are complete

## CLI Commands

### `harness init`

Creates or verifies:

- `.harness/`
- `.harness/harness.yml`
- `.harness/agents/common.md`
- `.harness/agents/start.md`
- `.harness/agents/planning.md`
- `.harness/agents/implementation.md`
- `.harness/agents/review.md`
- `.harness/agents/quality-check.md`
- `.harness/agents/done.md`
- `.harness/templates/session.md`
- `.harness/sessions/`
- `.env.example`
- `AGENTS.md` bootstrap instructions
- `.gitignore` rule for `.env`

This command must not overwrite user-edited templates, guardrails, or `AGENTS.md` without confirmation or an explicit force flag.

### `harness start <session-id> --linear WF-123`

Creates:

- `.harness/sessions/<session-id>/artifact.md`
- `.harness/sessions/<session-id>/proof/`

The `--linear` value records `linear_issue_key` in artifact metadata. It is not used as the folder name.

### `harness start <session-id> --create-linear`

Creates a Linear issue, then creates the local harness session linked to the returned Linear issue identifier and URL.

Requires:

- `LINEAR_API_KEY`
- `LINEAR_TEAM_ID`

Optional:

- `LINEAR_PROJECT_ID`
- `--title`
- `--description`

If `--title` is omitted, derive a readable title from `<session-id>`.

### `harness status <session-id>`

Prints:

- local artifact status
- linked Linear issue key, if present
- checklist completion summary
- missing requirements for the next transition
- common agent guardrail path
- current state agent guardrail path

Example output:

```text
Session: req-login-timeout
State: planning
Artifact: .harness/sessions/req-login-timeout/artifact.md
Common guardrail: .harness/agents/common.md
State guardrail: .harness/agents/planning.md
```

### `harness transition <session-id> <state>`

Validates and updates local artifact status. If Linear is configured, syncs the mirrored Linear status/comment after the local artifact update succeeds.

### `harness validate <session-id>`

Checks whether the artifact satisfies the requirements for its current state or target transition.

### `harness preflight-edit <session-id>`

Hard gate before product code edits.

Allows edits only when:

- artifact status is `implementation` or `needs-fix`
- implementation gate requirements are satisfied

Blocks edits in:

- `start`
- `planning`
- `review`
- `quality-check`
- `done`

### `harness approve-planning <session-id> --by <name>`

Records explicit human planning approval in artifact metadata and the `Planning Approval` section.

Required before:

- `planning -> implementation`

Agents must not run this command unless the user explicitly approves the plan.

### `harness approve-review <session-id> --by <name>`

Records explicit human review approval in artifact metadata and the `Human Review` section when needed.

Required before:

- `review -> quality-check`

Agents must not run this command unless the user explicitly approves the review.

### `harness attach-proof <session-id> <file>`

Copies or records proof under:

```text
.harness/sessions/<session-id>/proof/
```

Then adds a Markdown link to the artifact proof section.

### `harness sync-linear <session-id>`

Reads Linear credentials from `.env` and syncs:

- issue status
- transition summary comment
- proof summary comment

If `LINEAR_API_KEY` is missing, this command must fail clearly without changing the local artifact.

## Transition Guards

### Exit `planning`

Requires:

- acceptance criteria section is present
- validation plan section is present
- at least one checklist item exists
- open ambiguity questions are resolved or explicitly marked deferred

### Exit `implementation`

Requires:

- implementation checklist is updated
- relevant unit tests or test plan updates are noted
- changed areas are summarized

### Exit `review`

Requires:

- AI review result is recorded
- human review result is recorded
- review findings are converted into checklist items
- unresolved required findings transition back to `needs-fix`

### Exit `quality-check`

Requires proof matching the artifact validation plan:

- backend changes: unit test output and/or curl proof
- frontend changes: Playwright proof and screenshots
- manual auth/login blockers: human validation note

Failed validation transitions to `needs-fix` with checklist items added.

### Enter `done`

Requires:

- all mandatory checklist items complete
- required proof links present
- final human approval recorded
- Linear sync attempted when Linear linkage exists

## Linear Integration

Linear config is loaded in this precedence order:

1. Project `.env`
2. Global `~/.config/harness/.env`
3. Process environment variables

Supported keys:

```env
LINEAR_API_KEY=
LINEAR_TEAM_ID=
LINEAR_PROJECT_ID=
```

Behavior:

- Local artifact state is updated first.
- Linear sync happens after local state is valid.
- Missing project `.env` allows local-only operation.
- Missing `LINEAR_API_KEY` across all config sources blocks only Linear sync.
- Linear issue key is stored in artifact metadata.
- `harness start --create-linear` creates the Linear issue through GraphQL `issueCreate`.
- `harness sync-linear` resolves the issue, maps harness state to Linear workflow status, and updates the issue through GraphQL `issueUpdate`.
- Linear comments summarize transitions and proof, but do not duplicate the full artifact.
- Linear sync failure must report the error and leave the local artifact intact.

Default Linear state mapping:

```yaml
linear_state_map:
  start: Backlog
  planning: Planning
  implementation: In Progress
  review: Human Review
  needs-fix: In Progress
  quality-check: Quality Check
  done: Done
```

## Agent Skill and Template Plan

Create a root `AGENTS.md` bootstrap plus agent-facing instructions for each state.

### `AGENTS.md` Bootstrap

`AGENTS.md` must be small and stable. It teaches agents how to discover the active harness guardrails:

```md
# Harness Agent Bootstrap

For harness work:

1. Identify the session id from the user request or current artifact.
2. Run `bin/harness status <session-id>`.
3. Read `.harness/agents/common.md`.
4. Read the state-specific guardrail file printed by `harness status`.
5. Follow the state guardrails strictly.
6. Use `bin/harness transition` for phase changes.
7. Never bypass transition guards by editing artifact status manually.
8. Never write `.env` secrets into artifacts, logs, comments, or proof files.
```

The detailed rules live in `.harness/agents/` so they can evolve without bloating `AGENTS.md`.

### State Guardrails

Create these files:

- `.harness/agents/common.md`
- `.harness/agents/start.md`
- `.harness/agents/planning.md`
- `.harness/agents/implementation.md`
- `.harness/agents/review.md`
- `.harness/agents/quality-check.md`
- `.harness/agents/done.md`

Each state file defines:

- allowed actions
- forbidden actions
- required artifact updates
- required CLI commands
- exit criteria
- handoff behavior

State-specific intent:

- start: initialize harness files and verify CLI availability
- planning: ask ambiguity questions, explore repo, write acceptance criteria and validation plan
- implementation: only implement code/tests and fix approved review items
- review: run AI code review, record human review, add required fixes to checklist
- quality-check: execute validation plan, attach proof, route failures to `needs-fix`
- done: verify completion gates and sync Linear

These instructions guide agent behavior. They do not replace CLI validation.

## Test Plan

- `harness init` creates `.harness/`, templates, agent guardrails, `AGENTS.md`, `.env.example`, and `.gitignore` rule.
- `harness start req-login-timeout --linear WF-123` creates a local session folder without putting secrets in the path.
- `harness start req-login-timeout --create-linear --title "Login timeout"` creates a Linear issue and stores the returned issue key/URL.
- `harness status req-login-timeout` prints the current state, artifact path, common guardrail path, and state guardrail path.
- `harness status req-login-timeout` warns when non-harness files changed while the session is outside `implementation` or `needs-fix`.
- `harness preflight-edit req-login-timeout` blocks product code edits before planning has completed.
- `harness transition req-login-timeout implementation` blocks until `harness approve-planning req-login-timeout --by <name>` has been run.
- `harness transition req-login-timeout quality-check` blocks until `harness approve-review req-login-timeout --by <name>` has been run.
- `harness transition req-login-timeout planning` auto-syncs the Linear issue to `Planning` when Linear is configured.
- Missing `.env` allows local-only operation.
- Missing `LINEAR_API_KEY` blocks only Linear sync.
- Invalid transitions fail with actionable missing checklist fields.
- Valid transitions update artifact status and optionally sync Linear.
- Proof attachment records a local proof path in artifact.
- Linear sync failure does not corrupt local artifact state.

## Implementation Checklist

- [ ] Define `.harness/harness.yml` schema.
- [ ] Create `.harness/templates/session.md`.
- [ ] Build `bin/harness` command entrypoint.
- [ ] Implement `init`.
- [ ] Implement `start`.
- [ ] Implement `status`.
- [ ] Implement `validate`.
- [ ] Implement `transition`.
- [ ] Implement `attach-proof`.
- [ ] Implement `sync-linear`.
- [ ] Add tests for local-only flow.
- [ ] Add tests for missing Linear token.
- [ ] Add tests for invalid transition guards.

## Assumptions

- "Linear key" means Linear API token.
- First version supports one Linear issue per local harness session.
- Markdown artifact is canonical.
- Linear sync is optional.
- `.env` is local-only and never committed.
