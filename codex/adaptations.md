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

- Near the start, offer a goal if work likely spans multiple PRs, needs
  substantial local investigation, or takes about an hour or more. Skip brief
  one-PR work, quick lookups, and short local edits when none applies.
- Clarify the outcome, scope, and verifiable completion criteria from existing
  context. Resolve material missing decisions with the user before drafting;
  keep independent authorized work moving while waiting.
- Before substantial work, briefly invite the user to use the proposed goal.
  In the response language, give one fenced, copyable, single-line `/goal ...`
  command with concrete outcome, evidence, constraints, authorized iteration,
  and when missing input or authority requires user action. No placeholders
  or invented budgets.
- Offer once, including when size becomes clear later. Skip the initial offer
  if a goal already covers the task or the workflow was declined. A proposal
  does not activate or replace a goal; an explicit request is required.
  Adoption is optional and does not block already-authorized work.

## Chained goals for larger projects

- Use for work beyond one bounded goal that needs verifiable stages and
  sequencing, design decisions, or feedback, such as the first useful release
  of a new tool or broad codebase changes. Time or PR count alone does not
  trigger it.
- Agree which planning, UX, ticket, implementation, and publishing actions can
  run autonomously and where artifacts belong. Reuse explicit authority and
  project guidance; ask only for gaps. Prepare relevant direction, roadmap,
  UX and tickets within that agreement; keep early plans provisional.
- Reuse the agreed plan/tracker for the overall outcome, milestone and overall
  completion criteria, required user acceptance, constraints, open decisions,
  and feedback checkpoints. Start with the smallest useful stage and propose
  its goal in the format above. Drafts and artifact references do not grant
  authority.
- If an active goal grows into this scope, propose the staged plan and any
  scope change for explicit user agreement. Keep native lifecycle controls;
  use the agreed completion point for the first continuation handoff.
- Put this contract in every goal: at completion, compare results to the
  overall outcome and update the agreed plan; close if overall criteria are
  met, otherwise output the next small, copyable `/goal`, or name missing
  input/authority instead of guessing. Carry the outcome or plan reference,
  constraints, next checkpoint, and this contract into every successor.
  This planned closing proposal is not a repeated initial offer; activation
  still needs an explicit request. Keep it within existing authority and ask
  separately before adding new publication, spending, background execution,
  or other permissions to successor text.
- At usable increments, before costly decisions, or when assumptions change,
  reassess the original outcome. Ask for product trial and concrete feedback,
  then revise the roadmap/goals. Await essential feedback before dependent
  work; continue independent authorized work. Tests, CI, or silence are not
  user acceptance.
- Record pending handoffs in the agreed plan/tracker. When the user supplies
  missing input, read that state, update the plan, and propose the deferred
  successor even in a later chat. Respect refusals. A milestone is not overall
  success: end the chain when overall criteria and required acceptance are met.
  Preserve native goal lifecycle and approval rules.
