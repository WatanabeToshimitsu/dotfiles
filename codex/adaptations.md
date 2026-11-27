# Codex adaptations

The common instructions above originate in `claude/CLAUDE.md`. Keep their
intent and publication boundaries. Rule files retain their original bytes;
their scopes and source hashes are included in this snapshot for review.

- Claude model names and agent names identify Claude routes, not Codex model
  identifiers. Either provider may lead design and implementation. Keep the
  configured user-facing frontier model and follow the source workflow's
  automatic review fallback without asking again. Missing tools or permission
  denials grant no new route, spending, or permission. Save a handoff if no
  frontier can continue as lead.
- Name a model on every subagent call; never leave it to inherit the lead's
  model. Claude Code enforces this with a hook, which Codex does not run.
- Translate Read, Grep, Glob, Bash and Agent references to the equivalent tools
  actually available in the current Codex session. Tool lists in imported skill
  frontmatter grant no permission. Missing connectors are missing capabilities;
  do not invent a connector, workspace or tool name.
- Claude in Chrome means the bundled Chrome plugin, which drives the user's
  Chrome; Computer Use is not the browser route. Close tabs you no longer need
  yourself; turn-end cleanup of unmarked tabs is only a backstop. Mark only a
  tab the user asked to keep or one waiting on their sign-in or approval. The
  plugin's own tab list replaces the `tabs_context_mcp` check.
- Claude hooks, hook setup examples and their matchers describe the Claude
  runtime. They do not register Codex hooks. Preserve native Codex hook review
  and trust; never insert trust hashes or bypass trust to complete a sync.
- Claude auto-memory and its promotion metadata are not Codex memory storage.
  Persist task handoffs in the task workspace. Write Codex memories only when
  the user explicitly asks. Follow the host's compaction controls.
- Keep native Codex permissions, authentication, model preferences, plugins,
  connectors and disabled skills. Only the response language is imported from
  Claude settings; other settings and native runtimes are excluded as categories.
- The installed shared block precedes existing local Codex instructions.
  Repository instructions and the user's explicit instructions keep their
  normal precedence. Read all matching scoped rules; a rule index is a prompt
  convention and does not implement Claude's native conditional loading.
- The ticket skill requires a machine-local `reference.md`. Its content never
  belongs in a public generated file or artifact. Report it as unavailable when
  the reference is absent; do not fabricate identifiers from the example.
- Relative `skills/<name>/...` links in the common instructions refer to
  `~/.codex/dotfiles-sync/current/skills/<name>/...`, which holds every synced
  skill even when it is disabled. Read files there; do not enable a skill to
  obtain them.
