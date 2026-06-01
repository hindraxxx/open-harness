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

Forbidden:

- expanding scope without returning to planning
- marking review complete
- marking quality proof complete
