# Agent Orchestration

Treat Fable / Opus turns and the main conversation context as expensive resources. Delegate only when isolation, parallelism, or model routing has a clear payoff.

## Model Routing

- Use Fable / Opus for planning, architecture, difficult diagnosis, consequential decisions, and high-risk adversarial review.
- Use Sonnet for implementation, repository exploration, mechanical work, test execution, and ordinary focused review.
- Set a non-`inherit` `model` on every Agent call. A global hook rejects omitted or inherited models.
- Do not change the main conversation's model or effort repeatedly to route routine work; model and effort changes invalidate its prompt cache.

## When to Delegate

Use the main conversation for quick targeted changes, tightly coupled phases, or work that depends heavily on the current discussion.

Use a subagent when the task is self-contained, produces verbose output, benefits from a different model, or can run independently while useful parent work continues.

Do not delegate merely because an agent exists. Do not send multiple agents over the same files or question unless genuinely independent perspectives are required by high risk.

## Delegation Contract

Give each subagent a bounded task, relevant paths, constraints, expected output, and verification target. Ask it to return only:

- conclusion or changes made
- relevant file locations
- remaining risks or decisions
- verification results

Keep raw logs, full diffs, and large file contents out of the parent context. For large outputs, have the subagent summarize or write a scoped artifact.

## Review Routing

- Low risk: tests plus self review in the current context.
- Medium risk: one Sonnet focused review covering the changed behavior and likely failure modes.
- High risk: Fable / Opus adversarial review, adding a specialist only when the risk domain warrants it.
