# Planning State Guardrails

Explore first. Ask blocking ambiguity questions. Write acceptance criteria, validation plan, and implementation checklist.

Allowed:

- read/search files
- read `.harness/project/index.md` and the listed project-map files
- inspect existing behavior
- update stale or missing `.harness/project/` sections discovered during exploration
- write artifact planning sections in `.harness/sessions/<session-id>/artifact.md`
- ask user questions

Forbidden:

- product code edits
- test code edits
- route/controller/component changes
- proof completion

Exit only after human approval:

```bash
harness validate <session-id>
harness approve-planning <session-id> --by <human-name>
harness transition <session-id> implementation
```

`harness validate <session-id>` must show no missing planning fields before asking for human approval.

Agents must not run `approve-planning` unless the user explicitly instructs them to approve planning.

Before filling the session artifact:

1. Read `.harness/project/index.md` if present.
2. Verify relevant project-map facts by repo search or file inspection.
3. Update stale or missing project-map sections with verified facts.
4. Then fill `## Requirement Summary`, `## Acceptance Criteria`, `## Validation Plan`, and `## Implementation Checklist`.

Planning must include real checklist items in:

- `## Acceptance Criteria`
- `## Validation Plan`
- `## Implementation Checklist`

Do not transition to implementation with placeholder `TBD` checklist items.
