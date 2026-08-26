---
name: prepare-compaction
description: Prepare for context compaction by persisting the current task state, then give the user a ready-to-run /compact command and a continuation prompt. Use when the user says they want to compact the context ("compaction したい", "compact したい", "コンパクションしたい", "compact の準備").
---

# Prepare Compaction

Goal: after `/compact`, work must resume without re-discovering anything. Persist state first, then hand the user the exact command and the follow-up prompt.

## 1. Persist task state

Write a handoff file before anything else. Prefer the session memory directory (`<memory dir>/compaction-handoff.md`); fall back to the scratchpad directory if no memory directory is available. Overwrite any previous handoff file.

Include, using absolute paths and `file:line` references so nothing depends on conversation context:

- **Goal**: the user's original request in one or two sentences.
- **Done**: completed steps, with commit hashes / PR numbers if any.
- **In progress**: exactly where work stopped, including uncommitted files and their state.
- **Next steps**: ordered, concrete actions.
- **Key locations**: files, symbols, branches, and worktrees involved.
- **Decisions and constraints**: choices already agreed with the user, approaches rejected and why.
- **Verification**: commands that prove the work is correct (tests, lint, build).

When using the memory directory, follow the memory conventions (frontmatter with `type: project`, a pointer line in `MEMORY.md`) so the handoff also survives a brand-new session.

## 2. Present the compact command

Output a fenced block the user can copy, tailoring the Keep/Drop lists to the actual task:

```
/compact Keep: the task goal, next steps, decisions, and key file paths recorded in <handoff path>. Drop: raw tool output, file contents already persisted, and abandoned exploration.
```

## 3. Present the continuation prompt

Output a second fenced block for the user to paste right after compaction finishes:

```
Read <handoff path> and resume from its "Next steps" section. Verify the listed file references still match reality before editing. When the task is complete, delete the handoff file (and its MEMORY.md pointer line, if any).
```

Do not attempt to run `/compact` yourself; only the user can trigger it. End your reply by telling the user to run the command from step 2, then paste the prompt from step 3.
