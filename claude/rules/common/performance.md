# Model and Context Efficiency

Optimize expensive reasoning turns, not instruction size in isolation.

## Model Use

- Keep the main Fable / Opus context for planning, consequential judgment, and difficult diagnosis.
- Route implementation, exploration, mechanical work, and normal review to explicitly named Sonnet subagents when delegation has a clear payoff.
- Prefer the current context for small targeted work; a fresh subagent must rediscover local context.
- Avoid frequent main-session model or effort changes because they invalidate prompt caching.
- Use `high` as the normal effort balance. Raise depth only for a demanding decision or diagnosis, not as a permanent default.

## Context Management

- Delegate verbose tests, logs, documentation retrieval, and broad search when only a summary is needed in the parent.
- Do not send raw logs or full file dumps back from subagents.
- Use focused `/compact` when a long same-task history starts obscuring the active goal.
- Use `/clear` when switching to unrelated work with substantial old context.
- Do not interrupt a healthy low-utilization session merely to reduce token counts.

## Failure Loops

Read and classify a failure before retrying. Change the hypothesis or evidence on each retry, and stop repeated identical exploration. Use a Sonnet diagnosis subagent when the output is large or the investigation is self-contained; keep tightly coupled debugging in the main context.
