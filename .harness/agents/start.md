# Start State Guardrails

## Purpose

Initialize a harness session and prepare the artifact workspace.

## Allowed Actions

- Verify the harness CLI exists.
- Run `bin/harness init` if the project is not initialized.
- Run `bin/harness start <session-id> --linear <issue-key>` when a Linear issue is provided.
- Confirm session artifact and proof directory exist.
- Record the Linear issue key if present.

## Forbidden Actions

- Do not implement code.
- Do not write acceptance criteria beyond obvious metadata.
- Do not create proof manually outside the session proof directory.
- Do not store Linear API tokens in the artifact.

## Required Artifact Updates

- Session id.
- Initial status.
- Linked Linear issue key or explicit `none`.
- Creation timestamp if supported by the template.

## CLI Commands

- `bin/harness init`
- `bin/harness start <session-id> --linear <issue-key>`
- `bin/harness status <session-id>`

## Exit Criteria

- Session artifact exists.
- Proof directory exists.
- `bin/harness status <session-id>` prints the next guardrail path.

