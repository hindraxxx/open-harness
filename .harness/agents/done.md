# Done State Guardrails

## Purpose

Close the harness session after all required work, proof, and approvals are complete.

## Allowed Actions

- Verify final artifact completeness.
- Verify proof links resolve.
- Sync Linear if configured.
- Summarize final state and evidence.

## Forbidden Actions

- Do not implement new work.
- Do not add new acceptance criteria.
- Do not change final proof without recording why.
- Do not expose `.env` secrets in final summaries.

## Required Artifact Updates

- Final status.
- Final human approval.
- Proof summary.
- Linear sync result if applicable.

## CLI Commands

- `bin/harness status <session-id>`
- `bin/harness validate <session-id>`
- `bin/harness sync-linear <session-id>`

## Exit Criteria

- All mandatory checklist items complete.
- Proof links are present.
- Final approval is recorded.
- Linear sync is complete or failure is recorded.

