# SQLite-Only Harness Orchestrator

## Summary

Harness is now local-first. SQLite is canonical for orchestration state; Markdown remains the human-readable artifact used by agents.

## Architecture

- Agent operates the workflow.
- CLI enforces deterministic transition gates.
- `.harness/harness.db` stores canonical state.
- `.harness/sessions/<session-id>/artifact.md` stores readable requirement, checklist, review, quality, and final notes.
- Artifact frontmatter mirrors state for readability, but SQLite wins when they disagree.

## SQLite Model

Core tables:

- `sessions`: current state and artifact path.
- `transitions`: state movement history.
- `approvals`: planning/review approval records and planning hash.
- `review_passes`: timestamped AI review records.
- `required_fixes`: human-selected required fixes.
- `proofs`: attached proof paths.

## CLI Behavior

- `harness init`: creates `.harness/harness.db`, templates, guardrails, project map, and config.
- `harness start <session-id>`: creates DB session and Markdown artifact.
- `harness status <session-id>`: reads canonical state from SQLite.
- `harness transition <session-id> <state>`: validates gates, records transition, updates DB, mirrors frontmatter.
- `harness approve-planning`: records approval in DB, marks acceptance criteria checked, stores planning hash.
- `harness record-review`: appends AI review pass to DB and Markdown.
- `harness approve-review`: records human review approval in DB.
- `harness attach-proof`: copies proof, records DB row, mirrors Markdown proof link.
- `harness migrate-sqlite`: imports existing Markdown-only sessions.
- `harness doctor`: checks DB/artifact/proof integrity and frontmatter mirror mismatches.

## Validation Rules

- Planning requires requirement summary, acceptance criteria, validation plan, and implementation checklist.
- Implementation requires planning approval and matching planning hash.
- Implementation checklist must be complete before review.
- Review requires AI review, human review, review approval, and no unresolved human-selected required fixes.
- Quality-check requires executed validation plan, command/results, and proof files.
- Done requires quality pass and final approval.

## Quality Proof Policy

Configured in `.harness/harness.yml`:

```yaml
quality_gate:
  required_proof: auto
```

Supported values:

- `auto`
- `backend`
- `frontend`
- `both`
- `manual`

## Test Plan

- `harness init` creates `.harness/harness.db`.
- `harness start sample` creates DB session and Markdown artifact.
- Transitions update SQLite and mirror artifact frontmatter.
- SQLite state wins over artifact frontmatter.
- `harness migrate-sqlite` imports existing Markdown-only sessions.
- `harness doctor` reports mirror and proof integrity issues.
- Review passes, human-selected required fixes, and proofs are recorded in SQLite.
- Removed Linear commands fail as unsupported CLI commands.

## Assumptions

- SQLite path is `.harness/harness.db`.
- SQLite is canonical.
- Linear support is removed.
- Markdown remains required for agent-facing artifacts.
