# Review State Guardrails

Run AI review, record human review, and convert required findings into checklist items.

Forbidden:

- product code edits while still in review
- fixing review findings without transitioning to `needs-fix`

Required fixes go through:

```bash
harness transition <session-id> needs-fix
```

Quality-check requires explicit human approval:

```bash
harness approve-review <session-id> --by <human-name>
harness transition <session-id> quality-check
```

Agents must not run `approve-review` unless the user explicitly instructs them to approve review.

Before quality-check:

- `## Implementation Checklist` must be fully checked.
- `## Review > AI Review` must be filled.
- `## Review > Human Review` must be filled.
- `## Review > Required Fixes` must be `None.` or all required fix checklist items must be resolved through `needs-fix`.
