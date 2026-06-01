# Harness Agent Bootstrap

For harness work, these rules are mandatory.

1. Identify the session id from the user request or current artifact.
2. Run `harness status <session-id>`.
3. Read `.harness/agents/common.md`.
4. Read the state-specific guardrail file printed by `harness status`.
5. Follow the state guardrails strictly.
6. Before editing product code, run `harness preflight-edit <session-id>`.
7. Edit product code only when preflight exits 0.
8. Use `harness transition` for phase changes.
9. Never bypass transition guards by editing artifact status manually.
10. Never write `.env` secrets into artifacts, logs, comments, or proof files.

If the artifact status is `start`, `planning`, `review`, `quality-check`, or `done`, product code edits are forbidden.

If preflight blocks, stop and report the blocker.
