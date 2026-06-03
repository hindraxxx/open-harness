# Review State Guardrails

Run AI review, record findings, and wait for human review.

After running AI review, immediately record it in the artifact before responding:

```bash
harness record-review <session-id> --file review.md
```

or:

```bash
harness record-review <session-id> --ai "No blocking issues."
```

AI findings are advisory until the human decides. Do not add required fixes just because AI found something.

Only when the user explicitly decides a finding must be fixed, record it as a required fix:

```bash
harness record-review <session-id> --file review.md --required-fix "Fix validation gap"
```

A chat-only review is incomplete.

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
- `## Review > Required Fixes` must contain only human-selected required fixes.
- `## Review > Required Fixes` must be `None.` or all required fix checklist items must be resolved through `needs-fix`.
