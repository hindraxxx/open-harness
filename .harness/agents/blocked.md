# Blocked State Guardrails

Automation stopped after the recovery attempt limit or an external blocker.

Allowed:

- inspect the blocker report
- clarify requirements
- fix environment or dependency blockers
- record the human decision in the artifact
- transition back with `harness transition`

Forbidden:

- product code edits before transitioning back to `implementation`
- bypassing the blocked decision by editing artifact status manually

Common exits:

```bash
harness transition <session-id> planning
harness transition <session-id> implementation
harness transition <session-id> quality-check
harness transition <session-id> done
```
