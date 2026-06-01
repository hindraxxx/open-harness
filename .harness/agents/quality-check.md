# Quality Check State Guardrails

Run validation from the artifact and attach proof.

On entry:

0. Confirm `harness status <session-id>` shows state `quality-check` and `Missing: none`.
1. Read `## Validation Plan`.
2. Execute every unchecked validation checklist item that is automatable.
3. Mark executed validation items checked in `## Validation Plan`.
4. Record exact commands and results under `## Quality Check > Commands Run`.
5. Attach proof with `harness attach-proof <session-id> <file>`.
6. Run `harness validate <session-id>` before attempting `done`.

Forbidden:

- product code edits while still in quality-check
- inventing proof
- marking failed validation as complete

Failed validation goes through:

```bash
harness transition <session-id> needs-fix
```

Manual auth blockers require human validation notes, but quality-check still needs at least one attached proof file under `proof/`.
