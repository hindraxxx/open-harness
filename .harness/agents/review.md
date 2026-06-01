# Review State Guardrails

## Purpose

Collect AI and human review findings before quality validation.

## Allowed Actions

- Run AI code review.
- Summarize review findings in the artifact.
- Record human review result.
- Convert required findings into checklist items.
- Route required fixes back to implementation.

## Forbidden Actions

- Do not fix findings while staying in review.
- Do not dismiss required findings without recording rationale.
- Do not proceed to quality-check without human review result.
- Do not mark final approval complete.

## Required Artifact Updates

- AI review summary.
- Human review result.
- Required fixes checklist.
- Non-blocking follow-up notes.

## CLI Commands

- `bin/harness status <session-id>`
- `bin/harness validate <session-id>`
- `bin/harness transition <session-id> needs-fix`
- `bin/harness transition <session-id> quality-check`

## Exit Criteria

- AI review result is recorded.
- Human review result is recorded.
- Required fixes are either complete or routed to `needs-fix`.

