# Harness Agent Bootstrap

For harness work, these rules are mandatory. `.harness/agents/common.md` is the
canonical rule set; this file is the entry checklist.

0. If `harness` is not available, install it from the trusted harness repo:
   `curl -fsSL https://raw.githubusercontent.com/hindraxxx/open-harness/main/install.sh | bash`
   Then refresh the shell command cache with `hash -r` if available and continue.
   If installation is blocked by network or machine policy, stop and report the blocker.
1. If unsure the setup is healthy, run `harness doctor`.
2. Identify the session id from the user request, current artifact, or `harness list`.
   If no session exists yet, choose a short kebab-case session title that summarizes the request and create it with `harness start <session-title>` before continuing; the harness prefixes it as `YYYYMMDD_<session-title>`.
   If the user asks to split the current session/work/plan, treat "split" as a request for child-session planning under the current parent session. Use `harness split-session <parent-session-id> --story ...` in `planning` state instead of creating a separate top-level session, unless the user explicitly asks for an independent new session.
   You must also decide session structure proactively during planning: if the work decomposes into two or more independently shippable units, run `harness split-session` before filling the rest of the planning artifact. Do not wait to be asked.
3. Run `harness status <session-id>`.
4. Read `.harness/agents/common.md`.
5. Read `.harness/project/index.md` if present.
6. Read the state-specific guardrail file printed by `harness status`.
7. Follow the state guardrails strictly.
8. Before editing product code, run `harness preflight-edit <session-id>`.
9. Edit product code only when preflight exits 0.
10. Run `harness validate <session-id>` before every transition, then use
   `harness transition` for phase changes.
11. Never bypass transition guards by editing artifact status manually.
12. Never write `.env` secrets into artifacts, logs, comments, or proof files.

Project map rule: `.harness/project/` is orientation only. Current code wins; verify relevant facts before planning or editing.

Edit gate: product code edits are allowed only in `implementation` and `needs-fix`.
They are forbidden in `start`, `planning`, `review`, `quality-check`, `approval`,
`blocked`, and `done`.

Failure path: when a build, test, review, quality-check, or approval fails, run
`harness recover <session-id> --reason "<what failed>"` to drop into `needs-fix`.
After 3 recovery attempts the next recovery moves to `blocked` and stops automation.

If preflight blocks, stop and report the blocker.
