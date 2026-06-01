# Common Harness Agent Guardrails

## Required Startup

Before doing harness work:

1. Identify the session id.
2. Run `bin/harness status <session-id>`.
3. Read this file.
4. Read the state guardrail printed by `harness status`.
5. Work only within the current state rules.

## Always Do

- Treat `.harness/sessions/<session-id>/artifact.md` as canonical.
- Use `bin/harness transition` for state changes.
- Keep proof files under `.harness/sessions/<session-id>/proof/`.
- Record assumptions, open questions, review findings, and validation proof in the artifact.
- Preserve user changes. Do not overwrite existing artifact sections without reading them.
- Keep Linear as a mirror only. Local artifact state remains the source of truth.

## Never Do

- Do not bypass CLI transition guards by editing artifact status manually.
- Do not write `.env` secrets into artifacts, logs, comments, or proof files.
- Do not put `LINEAR_API_KEY` in folder names, Markdown, screenshots, or Linear comments.
- Do not move to `done` without final human approval and proof links.
- Do not invent acceptance criteria when ambiguity materially changes scope.

## Linear Rules

- Read Linear credentials only through `.env`.
- Store only non-secret Linear metadata in the artifact, such as issue key or URL.
- If Linear sync fails, keep local artifact state intact and record the sync failure.

