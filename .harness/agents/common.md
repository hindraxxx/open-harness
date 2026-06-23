# Common Harness Agent Guardrails

Before doing harness work:

1. Identify the session id from the user request, current artifact, or `harness list`.
2. If no session exists, choose a short kebab-case session id that summarizes the request and run `harness start <session-id>`.
3. Run `harness status <session-id>`.
4. Read this file.
5. Read `.harness/project/index.md` for project orientation when present.
6. Read the state guardrail printed by status.
7. Before editing product code, run `harness preflight-edit <session-id>`.

## Hard Rules

- SQLite is canonical for session state, transitions, approvals, and proofs.
- Markdown artifacts are required for planning, review, quality evidence, and human-readable notes.
- Use `harness transition` for phase changes.
- Never bypass CLI transition guards by editing artifact status manually.
- Never edit approval metadata or hashes manually.
- Never edit product code unless `harness preflight-edit <session-id>` exits 0.
- If preflight blocks, stop and report the missing phase or artifact requirements.
- Never write `.env` secrets into artifacts, logs, comments, or proof files.
- Do not fill review, quality-check, proof, or final approval sections before their state.
- Run `harness validate <session-id>` before every transition.
- Treat `.harness/project/` as orientation only. Verify relevant facts against current code before using them.
- If a project-map section is stale or missing during planning, update that section before filling the session artifact.

## Gate Order

1. `planning` -> `implementation`: requires filled requirement summary, acceptance criteria checklist, validation plan checklist, implementation checklist, and explicit human planning approval.
2. `implementation` -> `review`: requires the implementation checklist to be fully checked.
3. `review` -> `quality-check`: requires AI review, human review, no unresolved required fixes, and explicit human review approval.
4. `quality-check` -> `approval`: requires validation execution, recorded commands, and attached proof file under `proof/`.
5. `approval` -> `done`: requires explicit human quality approval.

## Edit Gate

Product code edits are allowed only in:

- `implementation`
- `needs-fix`

Product code edits are forbidden in:

- `start`
- `planning`
- `review`
- `quality-check`
- `approval`
- `blocked`
- `done`

## Auto Recovery

When implementation, review, quality-check, or approval fails, use:

```bash
harness recover <session-id> --reason "what failed"
```

This increments `recovery_attempts` and transitions to `needs-fix`. After 3 recovery attempts, the next recovery request transitions to `blocked` and stops automation.
Recovering from `quality-check` or `approval` clears any prior quality approval and resets `## Final Approval` to `TBD`.
