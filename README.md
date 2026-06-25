# Workflow Project Harness

Local CLI harness for agent-driven engineering workflows. It creates `.harness/` files in a repo, tracks session state in local SQLite, and gives agents guardrails for planning, implementation, review, and quality checks.

## Install

Host `install.sh` from this GitHub repo and share one bootstrap command across the team:

```bash
curl -fsSL https://raw.githubusercontent.com/hindraxxx/workflow-project/main/install.sh | bash
```

If your org prefers not to pipe into `bash`, use the safer two-step version:

```bash
curl -fsSLo install.sh https://raw.githubusercontent.com/hindraxxx/workflow-project/main/install.sh
bash install.sh
```

The installer:

- clones or updates the harness repo into `~/.workflow-project`
- symlinks the CLI into `~/.local/bin/harness`
- preserves the git checkout so `harness update` still works later

Manual fallback if you do not want the installer:

```bash
git clone <workflow-project-repo-url> ~/.workflow-project
chmod +x ~/.workflow-project/bin/harness
mkdir -p ~/.local/bin
ln -sf ~/.workflow-project/bin/harness ~/.local/bin/harness
```

## Start A Session

From your target repo:

```bash
harness start user-consent-request-id
harness status user-consent-request-id
```

`harness start <session-id>` auto-initializes missing local harness files, so most users do not need to run `harness init` separately.

Then tell your agent the session id:

```text
Use harness session user-consent-request-id.
```

If no session exists, the guardrails allow the agent to choose a short kebab-case session id and run `harness start <session-id>` itself.

Useful commands:

```bash
harness list
harness status <session-id>
harness validate <session-id>
harness preflight-edit <session-id>
harness history <session-id>
```

HTML artifacts regenerate when you run commands such as `harness status <session-id>` or a passing `harness validate <session-id>`.

## Update The CLI

From a target repo that already uses harness, update the installed harness source repo and refresh local guardrails when needed:

```bash
harness update
```

`harness update` pulls the `workflow-project` repo behind the running `bin/harness`, then refreshes the target repo's guardrails and records the current CLI version in `.harness/version`.

`harness start <session-id>` checks this version too. If local guardrails are outdated it prints a warning to run `harness update`, but it does not pull code or overwrite files during session start.

- `harness sync-guardrails` remains as a deprecated compatibility alias for the local refresh part of `harness update`.

## Test

From this repo:

```bash
python3 tests/test_harness_cli.py
```
