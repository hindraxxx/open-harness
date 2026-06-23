# Needs-Fix State Guardrails

Recovery state entered after a failed build, unit test, review, quality-check, or
approval. Product code edits are allowed here so the agent can fix the recorded
failure before returning through implementation.

On entry:

1. Confirm `harness status <session-id>` shows state `needs-fix`.
2. Read the recovery reason with `harness history <session-id>` and inspect the relevant artifact sections:
   - failed unit tests / build: `## Implementation Checklist` and `## Implementation Guidance`.
   - review fixes: `## Review > Required Fixes`.
   - quality failures: `## Validation Plan` and `## Quality Check > Commands Run`.
3. Re-read `### Old Flow`, `### New Flow`, `### Implementation Sketch`, `### Decision Flow`, and `### Code Anchors`
   before changing branch behavior.

Before editing product code, run:

```bash
harness preflight-edit <session-id>
```

Allowed:

- code edits required to resolve the recorded failure or required fix
- test edits required by the validation plan
- implementation/required-fix checklist updates

Required:

- Address only the recorded failure or human-selected required fixes. Do not expand scope.
- Resolve and check every required fix item before transitioning forward.
- Re-run the failing build/tests locally before transitioning.
- Run `harness validate <session-id>` before any transition.

Forbidden:

- expanding scope without returning to `planning`
- inventing proof or marking unresolved fixes complete
- editing approval metadata, hashes, or artifact status manually

Exits:

```bash
# return through implementation after fixes are complete
harness transition <session-id> implementation

# or stop automation if the recovery cannot be completed
harness transition <session-id> blocked
```

If fixes fail again, recover instead of forcing a transition:

```bash
harness recover <session-id> --reason "needs-fix retry failed: <summary>"
```

After 3 recovery attempts the next recovery moves the session to `blocked` and stops automation.
