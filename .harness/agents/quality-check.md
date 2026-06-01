# Quality Check State Guardrails

## Purpose

Execute the artifact validation plan and attach proof.

## Allowed Actions

- Run backend validation from the artifact, such as unit tests or curl checks.
- Run frontend validation from the artifact, such as Playwright checks and screenshots.
- Ask the user for manual validation when login, auth, or external access blocks automation.
- Attach proof files with `bin/harness attach-proof`.
- Record failed validation and route back to implementation.

## Forbidden Actions

- Do not change product code except trivial test harness fixes needed to run validation.
- Do not invent proof.
- Do not mark failed validation as complete.
- Do not proceed to done without final human approval.

## Required Artifact Updates

- Validation commands run.
- Results summary.
- Proof links.
- Manual validation notes when applicable.
- Failed checks converted into implementation checklist items.

## CLI Commands

- `bin/harness status <session-id>`
- `bin/harness validate <session-id>`
- `bin/harness attach-proof <session-id> <file>`
- `bin/harness transition <session-id> needs-fix`
- `bin/harness transition <session-id> done`

## Exit Criteria

- Required validation proof is attached.
- Failed validation items are fixed or routed to `needs-fix`.
- Final human approval is recorded before `done`.

