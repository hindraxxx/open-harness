# Workflow Project Harness

Local harness orchestrator for agent-driven engineering workflows.

Model:

- Agent calls the CLI.
- CLI manages session artifacts and state transitions.
- Markdown remains canonical.
- Linear is optional and mirrors state from global or project `.env` credentials.

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

## Configure Linear

Recommended: store Linear credentials once in the global harness env.

```bash
mkdir -p ~/.config/harness
cat > ~/.config/harness/.env <<'EOF'
LINEAR_API_KEY=lin_api_xxx
LINEAR_TEAM_ID=
LINEAR_PROJECT_ID=
EOF
chmod 600 ~/.config/harness/.env
```

The CLI reads config in this precedence order:

1. Project `.env`
2. Global `~/.config/harness/.env`
3. Process environment variables

Project `.env` is only needed for per-project overrides.

Optional project override:

```bash
cp .env.example .env
```

Fill only local secrets:

```env
LINEAR_API_KEY=lin_api_xxx
LINEAR_TEAM_ID=
LINEAR_PROJECT_ID=
```

Project `.env` is ignored by git. Do not place `LINEAR_API_KEY` in artifacts or proof files.

## Usage

Initialize harness files:

```bash
bin/harness init
```

Create a session:

```bash
bin/harness start req-login-timeout --linear WF-123
```

Or create the Linear issue automatically:

```bash
bin/harness start req-login-timeout --create-linear --title "Login timeout requirement"
```

`--create-linear` requires:

```env
LINEAR_API_KEY=lin_api_xxx
LINEAR_TEAM_ID=<team uuid>
```

Optional:

```env
LINEAR_PROJECT_ID=<project uuid>
```

You can add a description:

```bash
bin/harness start req-login-timeout \
  --create-linear \
  --title "Login timeout requirement" \
  --description "Harness planning session for login timeout behavior."
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

Attach proof:

```bash
bin/harness attach-proof req-login-timeout ./proof-output.txt
```

Sync Linear:

```bash
bin/harness sync-linear req-login-timeout
```

`harness start --create-linear` creates a real Linear issue through the GraphQL API.

`harness sync-linear` resolves the linked Linear issue, finds the mapped workflow status by name, and updates the issue state.

`harness transition` attempts Linear auto-sync after a successful local transition when the artifact has `linear_issue_key`.

Default Linear status mapping:

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

Edit `.harness/harness.yml` if your Linear workflow uses different status names.

## Upgrade Existing Project Guardrails

If a project already ran `harness init`, refresh its root `AGENTS.md` and `.harness/agents/*.md` guardrails:

```bash
harness upgrade-guardrails
```

Use this after CLI upgrades. It overwrites only the agent guardrail files and root `AGENTS.md`.

## Agent Flow

Tell an agent the session id. The agent should:

1. Read `AGENTS.md`.
2. Run `bin/harness status <session-id>`.
3. Read `.harness/agents/common.md`.
4. Read the state guardrail printed by status.
5. Run `bin/harness preflight-edit <session-id>` before product code edits.
6. Work within that state only.

## Test

Run:

```bash
python3 -m unittest discover -s tests
```
