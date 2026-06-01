# Implementation State Guardrails

Implement approved artifact checklist items and tests.

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
- Before reporting implementation complete, run `harness status <session-id>`.
- Do not summarize implementation as complete while any implementation checklist item remains unchecked.

Forbidden:

- expanding scope without returning to planning
- marking review complete
- marking quality proof complete
