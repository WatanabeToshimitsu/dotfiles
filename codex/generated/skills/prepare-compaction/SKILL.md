---
name: prepare-compaction
description: Prepare for context compaction by persisting the current task state, then give the user a ready-to-run /compact command and a continuation prompt. Use when the user says they want to compact the context ("compaction したい", "compact したい", "コンパクションしたい", "compact の準備").
---

# Prepare Compaction

Goal: after `/compact`, preserve agreed intent and resume from freshly recovered state.

## 1. Persist task context

Write a task-specific handoff file first. Use a private task workspace or scratchpad excluded from repository tracking, generation, and publication. Choose a unique name for this task and verify ownership before replacing or deleting it. Respect the client's memory policy; this workflow grants no memory-write authority.

Include only information that commands cannot recover:

- **Intent**: the task goal and user requirements not recorded in existing artifacts.
- **Decisions and constraints**: user agreements, authorization scope, and rejected options with their reasons.
- **Ownership**: who owns existing changes and current writer authority that repository or runtime inspection cannot establish.
- **Next action**: what to do next, what to verify, and unresolved decisions.

For recoverable facts, including GitHub state, commit history, diffs, check results, paths, and line numbers, record scoped read-only commands instead of copied results. Give commands the stable repository or evidence locators needed to run them after compaction. Recheck current state before editing.

## 2. Present the compact command

Output a fenced block the user can copy, tailoring the Keep/Drop lists to the actual task:

```
/compact Keep: the intent, decisions, ownership, next action, and recovery commands recorded in <handoff path>. Drop: raw tool output, cached Git/GitHub state, and file contents recoverable with commands.
```

## 3. Present the continuation prompt

Output a second fenced block for the user to paste right after compaction finishes:

```
Read <handoff path>, recover current state using its commands, and resume its "Next action". Preserve the recorded agreements and ownership; resolve missing or conflicting evidence before editing. When the task is complete, delete only this task's handoff file.
```

Do not attempt to run `/compact` yourself; only the user can trigger it. End your reply by telling the user to run the command from step 2, then paste the prompt from step 3.

## Codex portability

In Codex, use a task-local handoff file for compaction. Do not write Claude auto-memory or Codex memories without an explicit user request. Follow the host compaction controls; source slash commands are not executable shell commands.
