# Workflow Project Harness

Local CLI harness for agent-driven engineering workflows. It creates `.harness/` files in a repo, tracks session state in local SQLite, and gives agents guardrails for planning, implementation, review, and quality checks.

## Install

Host `install.sh` from this GitHub repo and share one bootstrap command across the team:

```bash
curl -fsSL https://raw.githubusercontent.com/hindraxxx/open-harness/main/install.sh | bash
```

If your org prefers not to pipe into `bash`, use the safer two-step version:

```bash
curl -fsSLo install.sh https://raw.githubusercontent.com/hindraxxx/open-harness/main/install.sh
bash install.sh
```

The installer:

- clones or updates the harness repo into `~/.workflow-project`
- symlinks the CLI into `~/.local/bin/harness`
- preserves the git checkout so `harness update` still works later

## Sessions

From your target repo:

```bash
harness start user-consent-request-id
harness status 20260605_user-consent-request-id
```

`harness start <session-title>` auto-initializes missing local harness files, prefixes the created session id as `YYYYMMDD_<session-title>`, and prints the canonical id to use with later commands.

Useful commands:

```bash
harness list
harness next <session-id>
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

`harness update` pulls the `open-harness` repo behind the running `bin/harness`, then refreshes the target repo's guardrails and records the current CLI version in `.harness/version`.

`harness start <session-title>` checks this version too. If local guardrails are outdated it prints a warning to run `harness update`, but it does not pull code or overwrite files during session start.

- `harness sync-guardrails` remains as a deprecated compatibility alias for the local refresh part of `harness update`.
