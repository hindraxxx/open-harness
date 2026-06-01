# Implementation State Guardrails

## Purpose

Implement approved work and tests from the artifact checklist.

## Allowed Actions

- Edit code required by the artifact.
- Add or update unit tests and integration tests.
- Fix review or quality-check findings assigned back to implementation.
- Update implementation checklist status.
- Record changed areas and test notes.

## Forbidden Actions

- Do not expand scope without returning to planning.
- Do not perform final quality proof.
- Do not mark review or human approval complete.
- Do not modify `.env` except when the user explicitly asks.

## Required Artifact Updates

- Implementation checklist progress.
- Changed files or changed areas summary.
- Test coverage notes.
- Any deviations from the original plan.

## CLI Commands

- `bin/harness status <session-id>`
- `bin/harness validate <session-id>`
- `bin/harness transition <session-id> review`

## Exit Criteria

- Approved implementation checklist items are addressed or explicitly blocked.
- Relevant tests are added or updated.
- Artifact records implementation status.

