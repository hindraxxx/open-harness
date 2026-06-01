# Planning State Guardrails

Explore first. Ask blocking ambiguity questions. Write acceptance criteria, validation plan, and implementation checklist.

Allowed:

- read/search files
- inspect existing behavior
- write artifact planning sections
- ask user questions

Forbidden:

- product code edits
- test code edits
- route/controller/component changes
- proof completion

Exit only after human approval:

```bash
harness approve-planning <session-id> --by <human-name>
harness transition <session-id> implementation
```

Agents must not run `approve-planning` unless the user explicitly instructs them to approve planning.
