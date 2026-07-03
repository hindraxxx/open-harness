# Common Harness Agent Guardrails

Before doing harness work:

1. Identify the session id from the user request, current artifact, or `harness list`.
2. If no session exists, choose a short kebab-case session title that summarizes the request and run `harness start <session-title>`; the harness prefixes it as `YYYYMMDD_<session-title>`.
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

## Split Session Requests

- Proactively decide session structure during `planning`: if exploration shows two or more independently shippable units of behavior, run `harness split-session <session-id> --story ...` before filling the rest of the planning artifact. Use the criteria in the Planning State Guardrails. Do not wait for the user to ask for a split.
- If the user asks to split the current session, work, plan, or analysis, treat "split" as child-session planning under the current parent session.
- Use `harness split-session <parent-session-id> --story ...` while the parent is in `planning`; transition from `start` to `planning` first if needed.
- Do not create a separate top-level session for a split request unless the user explicitly asks for an independent new session.
- Child story artifacts are coordination plans, not implementation sessions. Before editing product code for a child story, create a real repo-local session with `harness start-story <story-id> --repo <repo-path>` or link an existing one with `harness link-story <story-id> --repo <repo-path> --session-id <session-id>`, then continue inside that repo-local session.
- For multi-repo work, keep the parent artifact as the cross-repo user-story coordinator. Each child implementation session must live in the repo it edits and must not edit product code in sibling repos.
- Generated child story metadata starts with an empty `planning_session_id`; fill it only after a real child planning session exists and is intentionally linked.

## Final Response Gate

Before any final response during harness work:

1. Run `harness status <session-id>`.
2. If `Missing:` is not `none`, resolve every missing harness item that is allowed in the current state.
3. Run `harness validate <session-id>` before any allowed transition.
4. If validation passes and the current state can transition without human approval, run the required `harness transition <session-id> <next-state>`.
5. Stop only when the workflow is blocked by explicit human approval, failed validation, a required environment/proof blocker, or a harness transition guard.
6. In the final response, report the current harness state and the next required gate.

Passing tests or completing code is not enough to stop. Harness state must be clean or explicitly blocked.

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
Recovering from `review`, `quality-check`, or `approval` clears prior review approval and resets `## Review > Human Review` to `TBD`.
Recovering from `quality-check` or `approval` also clears quality approval, resets `## Final Approval` to `TBD`, and removes stale quality commands/proof/manual validation from the active gate.

## Sub-Agent Orchestration

- The main session is the orchestrator: it plans, delegates, routes verdicts, and verifies. It must not do broad exploration, product-code implementation, or code review inline when the role sub-agents are available.
- Runtime awareness: detect the current CLI. In Claude Code, spawn sub-agents via the Agent tool with subagent_type `code-explorer`, `implementer`, or `code-reviewer` (defined in `~/.claude/agents/*.md`). In Codex, spawn the same-named agents (defined in `~/.codex/agents/*.toml`). If the current runtime has none of these agents defined, state that in the response and perform the role inline — do not silently skip the workflow.
- Role-to-state mapping:
  - `planning`: fan out `code-explorer` (read-only, condensed reports, parallel for independent areas) before filling the planning artifact. The orchestrator constructs the plan itself; planning is never delegated. Orchestrator may do single-file targeted lookups; any multi-file sweep goes to `code-explorer`.
  - `implementation` / `needs-fix`: delegate code + unit tests + validation to `implementer` per checklist slice; it must return green test output.
  - `review`: delegate the AI review to `code-reviewer` (reviews the actual git diff; uses the code-review-expert skill). Route the verdict: APPROVE proceeds; REQUEST_CHANGES or P0/P1 findings loop back to `implementer`, then re-review until approved. P2/P3-only findings: fix via `implementer` or explicitly defer with a note.
  - `quality-check`: delegate the quality/cleanup pass (simplification, dead code, naming, consistency) and validation-command runs to `implementer`; re-review with `code-reviewer` only if the cleanup was non-trivial.
- Hard rules: `code-explorer` never edits; `implementer` never self-approves; `code-reviewer` never fixes. The orchestrator edits product code directly only for trivial mechanical fixes, and still only in `implementation` or `needs-fix` per the Edit Gate. Pass condensed context (explorer reports, review findings) between sub-agents explicitly — they do not share memory. Sub-agent delegation never bypasses harness gates: preflight-edit, validate, and transitions still run in the orchestrator.
