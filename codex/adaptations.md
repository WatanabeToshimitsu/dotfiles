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

## Long-task goal proposals

- At the start of a likely long task, clarify the desired outcome from the
  request and existing context; ask only for missing decisions that materially
  affect the objective, scope, or completion criteria.
  Resolve those decisions before drafting a complete goal; keep independent
  authorized work moving while waiting for answers.
- Offer a goal when the task is expected to span multiple PRs, require
  substantial open-ended local investigation, or take about an hour or more.
  These are rough estimates. Skip bounded one-PR changes, quick lookups, and
  short local edits when none of these triggers applies.
- After light scoping and before substantial work, briefly state the proposed
  objective and invite the user to use it with `/goal`. In the response
  language, provide one fenced block containing a complete, copyable
  `/goal ...` command on a single line. Include task-specific text for the
  desired outcome, verifiable completion criteria, scope and constraints,
  autonomous iteration within existing authorization, and when missing input
  or authority requires user action.
  Do not leave placeholders or invent a token budget.
- Suggest once per task; if its size becomes clear later, offer it then. Skip
  the suggestion when a goal already covers the task or the user has declined
  it. A suggestion does not create, replace, or activate a goal; do so only
  when explicitly requested. Preserve existing approval boundaries and keep
  progressing on authorized work without making adoption a prerequisite.
