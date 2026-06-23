# Planning State Guardrails

Explore first. Ask blocking ambiguity questions. Write acceptance criteria, validation plan, implementation guidance, and implementation checklist.

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
4. Then fill `## Requirement Summary`, `## Acceptance Criteria`, `## Validation Plan`, `## Implementation Guidance`, and `## Implementation Checklist`.

Planning must include real checklist items in:

- `## Acceptance Criteria`
- `## Validation Plan`
- `## Implementation Checklist`

`## Implementation Guidance` must be detailed enough for a lower-capability implementation agent to execute without re-planning. Include:

- expected file/function/module locations discovered during exploration
- current behavior to change or preserve
- a mandatory `### Overall Flow` subsection containing a Mermaid `sequenceDiagram` that shows the end-to-end request/data flow across relevant layers such as client, controller, application/domain service, repository/infrastructure, database, and external calls; label participants with exact discovered files, classes, modules, or call sites where possible, for example `ReportController.php`, `ReportService`, `ReportRepository`, or `PaymentGatewayClient`
- a mandatory `### Implementation Sketch` subsection containing all pseudocode, sample function shapes, and concrete code-shape steps the implementation agent can follow directly
- a mandatory `### Decision Table` subsection mapping each important branch/input state to the expected behavior, metric, return value, or side effect
- a mandatory `### Code Anchors` subsection naming the exact existing variables, conditions, helper functions, or call sites the implementation must use for key decisions
- invariants and out-of-scope areas that must not be changed
- concrete data cases or examples the implementer should verify

Do not put pseudocode or sample code in a separate top-level section. Keep it inside `### Implementation Sketch` so implementers find the intended code shape in one place.

When revising `## Implementation Guidance`, re-check `### Overall Flow` and update it if target files, dependencies, request/data path, side effects, or client-visible behavior changed.

Do not transition to implementation with placeholder `TBD` checklist items.
