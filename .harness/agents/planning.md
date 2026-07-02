# Planning State Guardrails

Explore first. Ask blocking ambiguity questions. Write acceptance criteria, validation plan, implementation guidance, and implementation checklist.

## Session Structure

Decide whether this work is one session or multiple child sessions before filling the rest of the artifact. Do not decide by story count alone.

Cluster the requirement into independent units of behavior. Each unit must be able to stand alone with its own Old Flow / New Flow sequence diagram, validation plan, and proof. A unit that only makes sense after another ships is a dependent story, not a separate session.

Use child sessions (split) when the work decomposes into two or more units that:

- have disjoint code surfaces (different endpoints, services, or screens with no shared edit surface that would cause merge conflicts if worked in parallel)
- can each be validated with an independent proof and acceptance criteria
- can be accepted or rejected independently

Keep a single session when the work is one cohesive change:

- one Old Flow / New Flow sequence diagram covers the end-to-end change cleanly
- acceptance criteria and validation plan apply to the whole change together
- splitting would produce sessions that cannot be understood or validated in isolation

If you decide to split, run `harness split-session <session-id> --story <story-id>:<title> ...` while this session is in `planning`. Fill each child's `dependencies` from the natural ordering of the work. Do not split just because the change is large; split only when units are independently shippable.

For multi-repo work, split by repo-owned behavior and then materialize each child in the repo that owns the code with `harness start-story <story-id> --repo <repo-path>`, or link an existing repo-local session with `harness link-story <story-id> --repo <repo-path> --session-id <session-id>`. The parent session stays as the cross-repo coordination artifact; child sessions are repo-local implementation artifacts.

If you are unsure, keep a single session. A session can be split later if implementation reveals genuinely independent work.

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
harness approve-planning <session-id>
harness transition <session-id> implementation
```

`harness validate <session-id>` must show no missing planning fields before asking for human approval.

Agents must not run `approve-planning` unless the user explicitly instructs them to approve planning.
`approve-planning` uses `whoami` for the approver name by default; pass `--by <human-name>` only to override it.

## Inline Annotations

The human can leave inline comments on the rendered plan and have you apply them, without leaving this planning session.

1. When the human wants to review the plan visually, run `harness serve <session-id>`. This opens the rendered `artifact.html` in their browser with an annotation layer; they highlight text, add comments, and click **Complete** when done. Comments accumulate in `.harness/sessions/<session-id>/annotations.json`.
2. Do **nothing** until the human explicitly asks you to act on the comments (for example "check my inline comments"). Do not act on annotations command output the moment it appears — wait for the human to ask.
3. When asked, run `harness annotations <session-id>` to read the open batch. Each entry gives the section, the resolved location in `artifact.md` (or a `stale` marker if the quoted text moved), the quoted text, and the human's comment.
4. Apply each requested improvement by editing `artifact.md` planning sections, then run `harness annotations <session-id> --resolve <annotation-id>` so the next round only surfaces new comments. Re-run `harness serve` whenever the human wants another editing pass.

Inline annotations are a planning-only refinement loop. They do **not** transition the session, do **not** become `## Review > Required Fixes`, and do **not** authorize product-code edits — they only refine the plan artifact.

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
- a mandatory `### Old Flow` subsection containing a Mermaid `sequenceDiagram` that shows the end-to-end request/data flow as it currently exists in the codebase across all relevant layers (client, controller, application/domain service, repository/infrastructure, database, and external calls); label participants with exact existing files, classes, modules, or call sites discovered during exploration, for example `ReportController.php`, `ReportService`, `ReportRepository`, or `PaymentGatewayClient`; for greenfield or new-feature work, prefer diagramming the surrounding integration boundary as it exists today — the existing systems, controllers, providers, and their interactions that the new feature will plug into. For a truly greenhorn change with no predecessor flow and no existing integration boundary to attach to, the `### Old Flow` subsection may be left empty; when you do, state explicitly why (for example `_No predecessor flow — greenfield change with no existing integration boundary._`) rather than leaving it blank, so implementers know the omission is deliberate
- a mandatory `### New Flow` subsection containing a Mermaid `sequenceDiagram` that shows the end-to-end request/data flow after the planned changes, with `alt`/`else` branches to distinguish scoped behavior changes from preserved existing behavior; label participants with exact existing files, classes, modules, or call sites where they overlap with the old flow
- a mandatory `### Implementation Sketch` subsection containing all pseudocode, sample function shapes, and concrete code-shape steps the implementation agent can follow directly
- a mandatory `### Code Anchors` subsection naming the exact existing variables, conditions, helper functions, or call sites the implementation must use for key decisions
- invariants and out-of-scope areas that must not be changed
- concrete data cases or examples the implementer should verify

Do not put pseudocode or sample code in a separate top-level section. Keep it inside `### Implementation Sketch` so implementers find the intended code shape in one place.

When revising `## Implementation Guidance`, re-check `### Old Flow` and `### New Flow` and update them if target files, dependencies, request/data path, side effects, or client-visible behavior changed.

Do not transition to implementation with placeholder `TBD` checklist items.
