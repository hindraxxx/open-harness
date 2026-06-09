# Approval State Guardrails

Human quality approval happens after validation proof exists.

On entry:

0. Confirm `harness status <session-id>` shows state `approval` and `Missing: none`.
1. Present `## Quality Check` commands, proof, and manual validation notes for human review.
2. Do not transition to `done` until the user explicitly approves the quality evidence.
3. Only after explicit user approval, run:

```bash
harness approve-quality <session-id> --by <human-name>
harness transition <session-id> done
```

Agents must not run `approve-quality` unless the user explicitly instructs them to approve quality evidence.

Forbidden:

- product code edits while still in approval
- changing validation output or proof
- inventing final approval

If quality evidence is rejected, use:

```bash
harness recover <session-id> --reason "quality approval rejected: <summary>"
```

Recovery clears quality approval and resets `## Final Approval` to `TBD`.
