---
name: eli15
description: Explain a concept, document, code change, or PR when the user asks for ELI15 or a fifteen-year-old-level explanation, including how it works and why the choices matter. Use eli5 for an unspecified simple explanation; do not use for an ordinary correctness review.
---

# ELI15

Explain the mechanism to a curious reader with general secondary-school
knowledge but no assumed expertise in the domain or repository. Treat
"fifteen" as a familiarity level, not the reader's age. Use the user's
language and requested length without talking down to them.

## Ground the explanation

- Resolve the subject from the request or current context. Ask one focused
  question only if the subject cannot be identified.
- Read the relevant source through available read-only tools. If it is
  inaccessible or only partly available, explain that limit and work from the
  supplied evidence; do not invent the missing content.
- Separate what the source demonstrates from inferred intent. Simplify the
  wording while retaining conditions, uncertainty, and important risks.

## Explain how and why

Start with the problem and intended outcome. For a change, give a concrete
before-and-after example, then trace the important causal steps or data flow.
Define necessary technical terms as they appear and connect them to that flow.

Explain a meaningful trade-off, boundary condition, or failure case when the
subject has one. Base the rationale on evidence; label an inferred reason.
Use a small example, code fragment, formula, or diagram only when it makes the
mechanism easier to follow. Map an analogy back to the real behavior and flag
where it stops applying. Add depth through causal explanation, not more jargon.

## When explaining a PR or diff

Read its stated purpose and relevant diff. Organize around behavior rather
than diff order. Give a short, prioritized reading route using file or symbol
references, with what to check at each stop and why it matters. Include relevant
edge cases and distinguish tests shown in the source and reported CI results
from checks actually executed. Make material evidence gaps explicit.

An explanation request alone does not authorize edits, test execution,
published comments, or approval of the change. Do not present this walkthrough
as a completed correctness review. Keep the structure proportional to the
question instead of filling a fixed template.
