# Workflow Project Harness

Local CLI harness for agent-driven engineering workflows. It creates `.harness/` files in a repo, tracks session state in local SQLite, and gives agents guardrails for planning, implementation, review, and quality checks.

## Install

Clone this repo somewhere stable:

```bash
git clone <workflow-project-repo-url> ~/workflow-project
chmod +x ~/workflow-project/bin/harness
```

Use it directly from any project:

```bash
~/workflow-project/bin/harness init
```

Recommended: symlink it into your system path:

```bash
sudo ln -sf ~/workflow-project/bin/harness /usr/local/bin/harness
```

## Start A Session

From your target repo:

```bash
harness init
harness start user-consent-request-id
harness status user-consent-request-id
```

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

`harness update` pulls the `workflow-project` repo behind the running `bin/harness`, then compares the target repo's `.harness/version` to the current CLI version. If the target guardrails are outdated, it runs the same overwrite path as:

```bash
harness sync-guardrails --force
```

`harness start <session-id>` checks this version too. If local guardrails are outdated it prints a warning to run `harness update`, but it does not pull code or overwrite files during session start.

- `harness sync-guardrails --force` overwrites agent guardrail files and bootstrap instructions.

## Test

From this repo:

```bash
python3 tests/test_harness_cli.py
```
