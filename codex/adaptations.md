# Codex adaptations

The common instructions above originate in `claude/CLAUDE.md`. Keep their
intent and publication boundaries. Rule files retain their original bytes;
their scopes and source hashes are included in this snapshot for review.

- Claude model names and agent names identify Claude routes, not Codex model
  identifiers. Either provider may lead design and implementation. Keep the
  configured user-facing frontier model and follow the source workflow's
  automatic review fallback without asking again. Record the actual provider,
  requested/observed model, and review level; never call advice or self-checks
  frontier approval. Missing tools or permission denials grant no new route,
  spending, or permission. Save a handoff if no frontier can continue as lead.
- Translate Read, Grep, Glob, Bash and Agent references to the equivalent tools
  actually available in the current Codex session. Tool lists in imported skill
  frontmatter grant no permission. Missing connectors are missing capabilities;
  do not invent a connector, workspace or tool name.
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
