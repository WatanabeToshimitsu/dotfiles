---
name: eli5
description: Explain a concept, document, code change, or PR in everyday language when the user asks for ELI5, a five-year-old-level explanation, or a simple first understanding without specifying a level. Do not use for ELI15 or an ordinary correctness review.
---

# ELI5

Give the reader a useful first understanding without assuming domain knowledge.
Treat "five" as a familiarity level, not the reader's age. Use the user's
language and requested length, with a respectful tone rather than baby talk.

## Ground the explanation

- Resolve the subject from the request or current context. Ask one focused
  question only if the subject cannot be identified.
- Read the relevant source through available read-only tools. If it is
  inaccessible or only partly available, explain that limit and work from the
  supplied evidence; do not invent the missing content.
- Separate what the source demonstrates from inferred intent. Simplify the
  wording while retaining conditions, uncertainty, and important risks.

## Build a simple mental model

Lead with what this is for and why it matters. For a change, show what happened
before and what happens afterward using a concrete situation.

Use familiar words. Define an essential technical term when introducing it;
leave unnecessary terms out. An everyday analogy can help, but do not force
one. Connect it back to the real behavior and flag a misleading limit.

Keep the explanation short and connected. Prefer one useful example over a
catalog of details. Avoid a file-by-file retelling or a rigid output template.

## When explaining a PR or diff

Read its stated purpose and relevant diff before explaining the change. Point
to one to three useful starting places with file or symbol references, saying
what the reader should check there and why. Describe these as review questions,
not proof that the change is correct. Distinguish tests shown in the source
and reported CI results from checks actually executed; mention material gaps.

An explanation request alone does not authorize edits, test execution,
published comments, or approval of the change. Do not present this walkthrough
as a completed correctness review.
