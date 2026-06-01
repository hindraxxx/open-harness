# Common Harness Agent Guardrails

Before doing harness work:

1. Identify the session id.
2. Run `harness status <session-id>`.
3. Read this file.
4. Read the state guardrail printed by status.
5. Before editing product code, run `harness preflight-edit <session-id>`.

## Hard Rules

- Treat `.harness/sessions/<session-id>/artifact.md` as canonical.
- Use `harness transition` for phase changes.
- Never bypass CLI transition guards by editing artifact status manually.
- Never edit product code unless `harness preflight-edit <session-id>` exits 0.
- If preflight blocks, stop and report the missing phase or artifact requirements.
- Never write `.env` secrets into artifacts, logs, comments, or proof files.

## Edit Gate

Product code edits are allowed only in:

- `implementation`
- `needs-fix`

Product code edits are forbidden in:

- `start`
- `planning`
- `review`
- `quality-check`
- `done`
