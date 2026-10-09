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
`approval_mode = "prompt"` with the app's `approvals_reviewer = "user"`.
GitHub CLI is also supported after the same publication review and explicit
approval coverage. In the user's Codex rules, replace the previous connector-only
`forbidden` entries for these commands with `prompt` entries; adding new rules
without removing the old entries leaves the stronger prohibition active:

```python
prefix_rule(pattern=["gh", "pr", "create"], decision="prompt", justification="Review the publication details and obtain explicit user confirmation before creating this PR. Never save permanent PR-creation approval.")
prefix_rule(pattern=["rtk", "gh", "pr", "create"], decision="prompt", justification="Review the publication details and obtain explicit user confirmation before creating this PR. Never save permanent PR-creation approval.")
prefix_rule(pattern=["rtk", "proxy", "gh", "pr", "create"], decision="prompt", justification="Review the publication details and obtain explicit user confirmation before creating this PR. Never save permanent PR-creation approval.")
```

Keep the existing force-push protections and unrelated rules. These entries
request runtime review; they do not grant unconditional permission.
Restart Codex after editing rule files: it loads them at startup. A running
session can retain an old prohibition even when `execpolicy check` confirms the
updated file. Finish active work before restarting the app.

Codex does not support a hook `permissionDecision: "ask"`. The hook therefore
blocks detected risks and returns inspection context for other PR attempts,
including CLI attempts. It does not open a human approval dialog or verify that
consent occurred. Under Auto-review, a CLI `prompt` can go to the automatic
reviewer, so it does not guarantee a human dialog either. The agent must establish
the user's explicit approval coverage **before invoking the tool**, reusing a
covered approval or obtaining missing consent; hook context is not consent.
Reuse an approval only within its repository, task, content, and limits; a
single-PR approval ends after that PR, and multiple PRs need explicit multiple,
split, or continued PR approval. The connector retains its separate native human
approval setting.

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
