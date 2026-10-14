# PR publication approval

Normal commits and pushes within the user's request do not need repeated
confirmation. Force pushes, including `--force-with-lease`, forced refspecs,
mirror updates, and remote deletions remain blocked by the publication guard.

For every PR, including a draft, the agent must prepare the exact repository,
base/head, title, body, and complete outgoing commit range. Inspect them for
secrets, personal data, confidential information, and content outside the
requested task, and report both the findings and any uninspected scope.

## Claude Code: automatic creation

When the task's authority includes delivery, Claude Code creates the PR with
`gh pr create` without a separate confirmation once the inspection is complete
and finds nothing. The agent asks before creating when findings, uninspected
scope, or out-of-scope content remain, and reports the created PR with its
inspection results afterwards.

The `gh pr create` spellings are in the `allow` list so the Auto mode classifier
does not gate clean PRs. The hook still decides first:

- A secret pattern in the title, body, body file, or commit range is denied.
- An incomplete inspection prompts the user. This covers text decided at run
  time (`--fill`, `--editor`, `--web`, `--template`, or a missing title or body),
  an unreadable body file, an unavailable or empty commit range, and a target or
  head that cannot be matched to `origin`: another remote, another host,
  `GH_HOST` or `GH_REPO`, a fork head, or commits not yet pushed to the head's
  `origin` branch.
- A complete, clean inspection proceeds and returns the report as context.

Connector PR tools stay in the `ask` list, because their target usually cannot
be matched to local commits. A hook `ask` forces a permission prompt even in
Auto mode ([hooks](https://code.claude.com/docs/en/hooks)).

## Shared limits

Stop on unresolved sensitive findings; resolve them with evidence, not an
annotation claiming a value is fake. PR creation grants no merge, issue closure,
profile, scheduling, spending, or private-data sharing authority. Native
rejection or cancellation stops that PR and dependent publication. Establish its
reason and affected scope before continuing; a human rejection is evidence to
reassess, not unused PR capacity. Never evade a denial through another route,
provider, or agent.

Report approval coverage and document checks separately from observed native
review, hook, and permission results. Document compliance does not prove runtime
permission or that future native confirmation will be skipped. Normal commits
and pushes, including later PR updates, retain their existing scope and guards.

## Codex: connector and CLI

Prefer the GitHub connector when available. Keep its PR-creation tool set to
`approval_mode = "prompt"`. To follow the reviewer selected for the session, remove
an app-specific `approvals_reviewer = "user"` override instead of forcing a human
prompt. An omitted app reviewer inherits `apps._default.approvals_reviewer`, then
the session's `approvals_reviewer`. Check those settings before changing the
local profile. This inheritance applies to all GitHub tool approval prompts;
preserve their individual approval modes and unrelated settings. Manual review
still asks the user, while Auto-review can approve, deny, or escalate according
to the action and its authorization. Reviewer selection grants no new authority
for merge, deletion, or other operations. Do not use unconditional `approve` or
disable native review to suppress repeated prompts.

GitHub CLI is also supported after the same publication review and explicit
authorization coverage. In the user's Codex rules, replace the previous connector-only
`forbidden` entries for these commands with `prompt` entries; adding new rules
without removing the old entries leaves the stronger prohibition active:

```python
prefix_rule(pattern=["gh", "pr", "create"], decision="prompt", justification="Verify the human user's message covers this repository, task, and operation, with inspection complete or individual approval for remaining scope. Reuse covered authorization; deny or escalate if evidence is missing. Never persist an allow rule from one-time consent.")
prefix_rule(pattern=["rtk", "gh", "pr", "create"], decision="prompt", justification="Verify the human user's message covers this repository, task, and operation, with inspection complete or individual approval for remaining scope. Reuse covered authorization; deny or escalate if evidence is missing. Never persist an allow rule from one-time consent.")
prefix_rule(pattern=["rtk", "proxy", "gh", "pr", "create"], decision="prompt", justification="Verify the human user's message covers this repository, task, and operation, with inspection complete or individual approval for remaining scope. Reuse covered authorization; deny or escalate if evidence is missing. Never persist an allow rule from one-time consent.")
```

Keep the existing force-push protections and unrelated rules. These entries
request runtime review; they do not grant unconditional permission.
Restart Codex after editing rule files: it loads them at startup. A running
session can retain an old prohibition even when `execpolicy check` confirms the
updated file. Finish active work before restarting the app.

Codex does not support a hook `permissionDecision: "ask"`. The hook therefore
blocks detected risks and returns inspection context for other PR attempts,
including CLI attempts. Context-only warnings do not pause execution and cannot
obtain consent for a late finding. The hook does not verify that consent occurred.
Under Auto-review, a CLI `prompt` can go to the automatic reviewer, which sees
the approval request and a compact transcript, not just the rule justification.
The agent must complete inspection and establish the user's explicit
authorization **before invoking the tool**; hook context and
automatic review are not user consent. Reuse explicit continuing, split, or
multi-PR authorization for inspected operations within its stated targets,
actions, data scope, duration, and limits. Without a stated wider scope, limit
approval to the current task and repository in the current conversation. Do not
reconstruct permission from memory or a public issue. A single-PR approval ends
after that PR and never creates a persisted allow rule.

Conversation consent does not automatically become a profile setting. To carry
continuing permission into a new conversation, the user must restate its scope
or explicitly authorize a persistent scoped instruction. Include that source
in the new approval context; do not infer permission when its basis is missing.

Ask only for missing or ambiguous authorization, expanded scope, or unresolved
inspection concerns. A user's explicit requirement for per-action confirmation
still applies; generic hook reminders or older document defaults do not revoke
an explicit continuing authorization. If the hook cannot inspect a range, obtain
authorized read-only evidence or individual approval covering that remaining
scope before invocation. If a late warning reveals a missed check, report the
gap and stop further publication until it is resolved. Inspection and consent
remain agent prerequisites assessed by native review, not facts mechanically
verified by this hook. Unresolved sensitive findings and native denials always
stop the action.

PR creation does not itself authorize image uploads. When the user explicitly
includes attachments, view each image and check that its content and GitHub
destination are covered before reusing that authorization. Browser site access,
upload approval, and connector approval are separate controls; changing PR
instructions or the connector reviewer does not establish that upload prompts
will disappear. Diagnose the actual upload route before changing its settings.

Update the shared source and regenerate Codex instructions through the normal
sync workflow. Apply the installer only after integration, from the canonical
`main` checkout matching the last fetched `origin/main`; it rejects unmerged
branches. Until then, both managed instructions and the live canonical hook keep
their old wording. The installer preserves local text after its managed block, so
check that suffix for old unconditional confirmation rules separately. Change
only the authorized local policy with a private backup; do not hand-edit the
managed block or native hook trust. If the live hook points at the canonical
checkout, it retains its old wording until that checkout receives the change.
A current local policy may clarify that explicit user authorization takes
precedence over that reminder, but never over a native denial. Report which
parts are applied, require integration or restart, or remain unverified in the GUI.

Codex PR creation through `gh api` remains blocked because its request body and
target diff are not fully inspected by this hook. Use `gh pr create` with an
explicit target and body instead. Read-only API calls are unaffected.

For Codex CLI creation, supply a nonempty `--title` and either `--body` (which
may be explicitly empty) or a readable `--body-file`. The hook blocks missing
text, stdin, unreadable or oversized body files, and options that generate or
edit text after inspection, such as `--fill`, `--editor`, `--web`, `--template`,
`--recover`, and `--attach`. Unrecognized flags and combined short flags are
also blocked. Prepare the final text before checking its approval coverage.

The native Codex Bash payload observed on 2026-09-14 contained
`tool_input.command` and the session `cwd`, but no tool-level `workdir`.
Setting a shell tool's working directory alone therefore did not select the
repository inspected by the guard. For `git push`, put a literal absolute
repository path in the command so the guard can inspect the actual target:

```bash
rtk proxy git -C /absolute/repo push origin topic
```

Use absolute `--body-file` paths for Codex CLI PR creation. PR commit-range
inspection still uses the session cwd and may be incomplete. Review the complete
outgoing range separately and disclose uninspected scope for individual approval.

Automatic commit inspection is best-effort: a missing base, repository mismatch,
fork head, or oversized history produces an uninspected-range warning, not a
denial. The agent must review the complete outgoing range separately, for example
through the connector, and obtain individual approval for anything it cannot
inspect. This preserves PRs whose remote commits cannot be resolved locally.
Body files can change between hook inspection and execution; use inline `--body`
when that risk matters, and do not edit an approved body file before creation.

Claude uses the hook `ask` decision only for incomplete inspections, as described
above. Secret detection and history-rewrite checks run before the client-specific
approval behavior.

## Verification

Run `python3 -B -m unittest discover -s claude/hooks/tests -p test_remote_mutation_guard.py`.
Check the active CLI policy without publishing anything:

```bash
codex execpolicy check --rules ~/.codex/rules/default.rules -- gh pr create --title Test --body Clean
codex execpolicy check --rules ~/.codex/rules/default.rules -- git push origin topic
codex execpolicy check --rules ~/.codex/rules/default.rules -- git push --force origin topic
```

Expected decisions are `prompt`, `allow`, and `forbidden`. These are policy
checks, not real PR creation or push commands. They do not prove that a model
will follow every instruction or that a pattern scan detects every secret.
The prefix-rule checks cover the exact command spellings shown. Other wrappers
can fall through to Codex's default review behavior; the hook separately unwraps
supported commands to inspect risky arguments, including force flags.
Use the documented `gh pr create` spelling. Aliases such as `gh pr new`, custom
aliases, extensions, and edits after PR creation are outside this hook's coverage.
For example, `git push origin topic --force` can match a broad `allow` prefix;
the hook must still reject it. Keep the hook enabled alongside the rules.

References: [Codex hooks](https://learn.chatgpt.com/docs/hooks#pretooluse),
[Auto-review](https://learn.chatgpt.com/docs/sandboxing/auto-review), and
[configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference),
[rules](https://learn.chatgpt.com/docs/agent-configuration/rules),
and [GitHub CLI PR creation](https://cli.github.com/manual/gh_pr_create).
