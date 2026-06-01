# Workflow Project Harness

Local harness orchestrator for agent-driven engineering workflows.

Model:

- Agent calls the CLI.
- CLI manages session artifacts and state transitions.
- Markdown remains canonical.
- Linear is optional and mirrors state from `.env` credentials.

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

Copy the example env file:

```bash
cp .env.example .env
```

Fill only local secrets:

```env
LINEAR_API_KEY=lin_api_xxx
LINEAR_TEAM_ID=
LINEAR_PROJECT_ID=
```

`.env` is ignored by git. Do not place `LINEAR_API_KEY` in artifacts or proof files.

## Usage

Initialize harness files:

```bash
bin/harness init
```

Create a session:

```bash
bin/harness start req-login-timeout --linear WF-123
```

Check status and guardrails:

```bash
bin/harness status req-login-timeout
```

Validate the current state:

```bash
bin/harness validate req-login-timeout
```

Move state:

```bash
bin/harness transition req-login-timeout planning
bin/harness transition req-login-timeout implementation
```

Attach proof:

```bash
bin/harness attach-proof req-login-timeout ./proof-output.txt
```

Sync Linear:

```bash
bin/harness sync-linear req-login-timeout
```

Linear sync is currently a safe local stub: it validates `.env` and records a sync note in the artifact. Real API calls can be added after the local flow is stable.

## Agent Flow

Tell an agent the session id. The agent should:

1. Read `AGENTS.md`.
2. Run `bin/harness status <session-id>`.
3. Read `.harness/agents/common.md`.
4. Read the state guardrail printed by status.
5. Work within that state only.

## Test

Run:

```bash
python3 -m unittest discover -s tests
```

