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

## Promotion

Auto memory is visible only to Claude Code. A `feedback` memory reaches the other
agents that read [`../CLAUDE.md`](../CLAUDE.md) only once it is promoted into
`CLAUDE.md`, `claude/CLAUDE.md`, `claude/rules/`, or a skill in `claude/skills/`.

Record where a memory was promoted in its own frontmatter, next to `type`:

```yaml
metadata:
  type: feedback
  promoted: claude/CLAUDE.md
```

The value is a path relative to the repository root, or `none` when the memory is
deliberately kept out of durable configuration. `dotfiles-doctor.sh` reports a
`feedback` memory with no `promoted` field as a promotion candidate, and reports a
`promoted` path that no longer exists. Missing the field is what makes a new
memory a candidate, so nothing has to be remembered for the report to appear.

The memory directory belongs to Claude Code, not to this repository, so the check
stays silent when the directory is absent rather than failing the whole report.

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
