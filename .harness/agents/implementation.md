# Implementation State Guardrails

Implement approved artifact checklist items and tests.

Before implementation:

1. Read `## Implementation Guidance`.
2. Read `### Old Flow` to understand the current end-to-end request/data path as it exists today. It may be empty for a greenhorn change with no predecessor flow, as long as it states why — an empty Old Flow with an explicit note is not a missing diagram.
3. Read `### New Flow` to understand the target end-to-end request/data path, branch behavior, and expected side effects after changes.
4. Follow the `### Implementation Sketch` as the starting code plan.
5. Use `### Code Anchors` for the exact existing variables, conditions, helpers, and call sites to modify or preserve.
6. If the diagrams, sketch, or code anchors are missing, ambiguous, or conflict with current code, stop and return to planning instead of re-planning silently. A deliberately empty `### Old Flow` that states why (greenhorn change with no predecessor) does not count as missing.

Before editing product code, run:

```bash
harness preflight-edit <session-id>
```

Allowed:

- code edits required by acceptance criteria
- test edits required by validation plan
- implementation checklist updates

Required:

- After completing each implementation task, check its item in `## Implementation Checklist`.
- Implementation is not complete when code edits are done or tests pass.
- Implementation is complete only after every implementation checklist item is checked, `harness validate <session-id>` passes, and `harness transition <session-id> review` succeeds or reports an explicit blocker.
- Before reporting implementation complete, run `harness status <session-id>` and resolve any `Missing:` items allowed in `implementation`.
- Do not summarize implementation as complete while any implementation checklist item remains unchecked or while `harness status` reports missing implementation items.
- After every implementation checklist item is checked, run `harness validate <session-id>` and transition to `review` if validation passes.
- Do not run validation plan commands, browser validation, screenshots, or proof attachment in `implementation`.
- If build or unit tests fail during implementation, run `harness recover <session-id> --reason "unit test failed: <summary>"` and fix from `needs-fix`.

Forbidden:

- expanding scope without returning to planning
- marking review complete
- marking quality proof complete
- recording `## Quality Check` commands/proof/manual validation before `quality-check`
