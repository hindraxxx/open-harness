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

