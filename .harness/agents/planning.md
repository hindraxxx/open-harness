# Planning State Guardrails

## Purpose

Turn the requirement into acceptance criteria and a validation plan.

## Allowed Actions

- Explore the repo before writing the plan.
- Ask targeted ambiguity questions when scope, behavior, or success criteria are unclear.
- Write acceptance criteria.
- Write validation and harness plan.
- Add implementation checklist placeholders.
- Identify backend, frontend, manual, or mixed validation needs.

## Forbidden Actions

- Do not implement code.
- Do not update production config.
- Do not mark proof complete.
- Do not transition forward while blocking ambiguity remains.

## Required Artifact Updates

- Requirement summary.
- Acceptance criteria.
- Validation plan.
- Implementation checklist.
- Open questions or resolved assumptions.

## CLI Commands

- `bin/harness status <session-id>`
- `bin/harness validate <session-id>`
- `bin/harness transition <session-id> implementation`

## Exit Criteria

- Acceptance criteria exist.
- Validation plan exists.
- At least one implementation checklist item exists.
- Blocking ambiguity is resolved or explicitly deferred.

