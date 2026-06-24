# Review State Guardrails

Run AI review, record findings, and wait for human review.

Entering `review` is not a stopping point. After a successful `implementation -> review`
transition, immediately perform the AI review and record it before responding, unless a
harness command fails.

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

Review is complete only after:

- `## Review > AI Review` is filled by `harness record-review`.
- Any human-selected required fixes are either absent or routed through `needs-fix`.
- `harness status <session-id>` reports no review items missing except explicit human approval.
- The user explicitly approves review before `harness approve-review` is run.

Forbidden:

- product code edits while still in review
- fixing review findings without transitioning to `needs-fix`

Required fixes go through:

```bash
harness recover <session-id> --reason "open review item: <summary>"
```

Recovery clears prior review approval and resets `## Review > Human Review` to `TBD`.

Quality-check requires explicit human approval:

```bash
harness approve-review <session-id>
harness transition <session-id> quality-check
```

Agents must not run `approve-review` unless the user explicitly instructs them to approve review.
`approve-review` uses `whoami` for the approver name by default; pass `--by <human-name>` only to override it.

Before quality-check:

- `## Implementation Checklist` must be fully checked.
- `## Review > AI Review` must be filled.
- `## Review > Human Review` must be filled.
- `## Review > Required Fixes` must contain only human-selected required fixes.
- `## Review > Required Fixes` must be `None.` or all required fix checklist items must be resolved through `needs-fix`.
