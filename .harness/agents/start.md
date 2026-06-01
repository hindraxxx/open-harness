# Start State Guardrails

Initialize the harness session.

Allowed:

- verify harness files
- create or inspect the session artifact
- transition to `planning`

Forbidden:

- product code edits
- test code edits
- implementation decisions

Before any code edit, transition to `planning`, complete planning, then transition to `implementation`.
