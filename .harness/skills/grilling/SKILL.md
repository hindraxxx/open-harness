---
name: grilling
description: Grill the user relentlessly about a plan or design. Use when the user wants to stress-test a plan before building, or uses any 'grill' trigger phrases.
---

# Grilling

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask the questions one at a time, waiting for feedback on each question before continuing. Asking multiple questions at once is bewildering.

If a *fact* can be found by exploring the codebase, look it up rather than asking me. The *decisions*, though, are mine — put each one to me and wait for my answer.

Stop asking once there are no open decisions left. Walk the design tree until every branch that would change the plan is resolved, then stop — do not invent filler questions to keep going, and do not re-ask what is already settled. When the only things left are facts you can look up or decisions I have already made, tell me grilling is complete and summarize what we agreed.

Do not enact the plan until I confirm we have reached a shared understanding.

## Use in the harness planning state

This skill backs the grilling protocol in `.harness/agents/planning.md`. Run it
during the `planning` state, after exploration and before filling
`artifact.md`, to sharpen the requirement:

- Resolve *facts* (target files, current behavior, data flow, validation
  surfaces) by reading the repo — do not ask about anything the code can answer.
- Put every open *decision* (scope, success criteria, edge cases, out-of-scope
  boundaries) to the human one question at a time, each with your recommended
  answer.
- Record resolved answers directly in the relevant `artifact.md` planning
  sections.
- Do not `harness approve-planning` or transition to `implementation` until the
  human confirms shared understanding.

## Attribution

Adapted from Matt Pocock's `grilling` skill:
https://github.com/mattpocock/skills/blob/main/skills/productivity/grilling/SKILL.md
