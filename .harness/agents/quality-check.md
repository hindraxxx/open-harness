# Quality Check State Guardrails

Run validation from the artifact and attach proof.

## Bounded Worker Mode

Quality-check agents should execute the approved `## Validation Plan` as written.
Do not invent additional validation scope or search broadly for alternative
checks. Read only the validation plan, proof expectations, command outputs, and
files directly needed to run or attach the approved proof. If the validation
plan is incomplete, recover to `needs-fix` or return to planning with the exact
gap instead of expanding validation silently.

On entry:

0. Confirm `harness status <session-id>` shows state `quality-check` and `Missing: none`.
1. Read `## Validation Plan`.
2. Execute every unchecked validation checklist item that is automatable.
3. Mark executed validation items checked in `## Validation Plan`.
4. Record exact commands and results under `## Quality Check > Commands Run`.
5. Attach proof with `harness attach-proof <session-id> <file>`.
6. Run `harness validate <session-id>`.
7. Transition to `approval` and stop for human quality approval.

Forbidden:

- product code edits while still in quality-check
- inventing proof
- marking failed validation as complete

Failed validation goes through:

```bash
harness recover <session-id> --reason "quality check failed: <summary>"
```

Recovery clears prior review approval, quality approval, and active quality evidence. The next pass must re-enter review and record fresh quality commands/proof/manual validation.

Manual auth blockers require human validation notes, but quality-check still needs at least one attached proof file under `proof/`.

Proof policy is configured in `.harness/harness.yml`:

- `auto`: infer backend/frontend expectations from the validation plan and project map.
- `backend`: require a curl command and sample response.
- `frontend`: require screenshot proof and view validation notes.
- `both`: require backend and frontend proof.
- `manual`: require generic proof only.
