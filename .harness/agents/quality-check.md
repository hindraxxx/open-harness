# Quality Check State Guardrails

Run validation from the artifact and attach proof.

Forbidden:

- product code edits while still in quality-check
- inventing proof
- marking failed validation as complete

Failed validation goes through:

```bash
harness transition <session-id> needs-fix
```

Manual auth blockers require human proof notes.
