# Harness Agent Bootstrap

For harness work, these rules are mandatory. `.harness/agents/common.md` is the
canonical rule set; this file is the entry checklist.

0. If unsure the setup is healthy, run `harness doctor`.
1. Identify the session id from the user request or current artifact. If no session
   exists yet, create one with `harness start` before continuing.
2. Run `harness status <session-id>`.
3. Read `.harness/agents/common.md`.
4. Read `.harness/project/index.md` if present.
5. Read the state-specific guardrail file printed by `harness status`.
6. Follow the state guardrails strictly.
7. Before editing product code, run `harness preflight-edit <session-id>`.
8. Edit product code only when preflight exits 0.
9. Run `harness validate <session-id>` before every transition, then use
   `harness transition` for phase changes.
10. Never bypass transition guards by editing artifact status manually.
11. Never write `.env` secrets into artifacts, logs, comments, or proof files.

Project map rule: `.harness/project/` is orientation only. Current code wins; verify relevant facts before planning or editing.

Edit gate: product code edits are allowed only in `implementation` and `needs-fix`.
They are forbidden in `start`, `planning`, `review`, `quality-check`, `approval`,
`blocked`, and `done`.

Failure path: when a build, test, review, quality-check, or approval fails, run
`harness recover <session-id> --reason "<what failed>"` to drop into `needs-fix`.
After 3 recovery attempts the next recovery moves to `blocked` and stops automation.

If preflight blocks, stop and report the blocker.
