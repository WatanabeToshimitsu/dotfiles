Perform exactly one bounded, read-only maintenance check, then stop.

1. Inspect the current conversation and repository state only to determine
   whether explicitly authorized unfinished work or the current branch's pull
   request needs attention.
2. Do not edit files or change Git, GitHub, or any external service. Do not
   start cleanup, bug hunts, simplification, or a new initiative. Do not use
   Monitor.
3. If actionable work exists, report it for a person or an approved
   project-level Loop contract. Otherwise, say briefly that nothing is pending.
4. End this self-paced loop now by calling `ScheduleWakeup` with `stop: true`.
   Do not schedule another wakeup or create a scheduled task.

A project can replace this fallback with `.claude/loop.md`, which Claude Code
loads before this user-level prompt.
