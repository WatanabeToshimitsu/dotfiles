# Claude Code auto memory

Claude Code introduced auto memory in 2.1.59 and repository-scoped worktree
sharing in 2.1.63. In 2.1.63 and later, the main checkout, linked worktrees, and
subdirectories share one repository-scoped directory under:

```text
~/.claude/projects/<repository>/memory/
```

This repository does not override that behavior with a `SessionStart` hook.
On 2026-08-26, Claude Code 2.1.231 reported the same auto-memory directory from
the main dotfiles checkout and a linked worktree while user hooks were excluded.

## Legacy data

- Back up the repository-scoped memory directory before changing memory setup.
- Keep `~/.claude/worktree-memory-archive/` as recovery-only data. It is not an
  active memory source and must not be imported automatically.
- Old worktree `memory` symlinks are inert with repository-scoped auto memory.
  Remove them manually only after confirming their targets are backed up.
- The retired `~/.claude/homunculus/` tree is not an active learning source.
  Archive it outside active configuration rather than importing raw event logs.
  Its `evolved/` and `instincts/` trees contained no generated artifacts. The
  remaining identity duplicated the active language and experience settings,
  while the JSONL files contained tool-event telemetry and invalid records.
  The audit therefore found no unique knowledge to migrate.

To roll back the hook removal, revert the change and run
`bash install.sh --symlinks-only`.

References:

- <https://code.claude.com/docs/en/memory>
- <https://code.claude.com/docs/en/changelog>
