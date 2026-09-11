# Claude to Codex sync feasibility

Implementation handoff: [issue #124](https://github.com/WatanabeToshimitsu/dotfiles/issues/124).

The transport and generation mechanics work. A disposable probe passed 15
checks on macOS with `codex-cli 0.154.0` on 2026-09-11. Codex discovered all six
linked repository skills and observed a source edit after `forceReload`.
This is a feasibility spike, not an installer or a completed migration.

The user requested a separate worktree investigation followed by an
implementation issue. Production Claude/Codex settings, installation scripts,
workflows, and the original working tree were not changed. No model turn or
external-agent import was started. This spike may be inspected or cherry-picked
by another session; it must not be enabled as production policy.

## Reproduce the recorded result

Source baseline: `6785e9720a049ec91a15e11f499bffa7393db1a6` (`origin/main` when
the worktree was created). Uncommitted configuration changes in the original
checkout and the unfinished work for issue #121 were not part of that baseline.

Requirements: Python 3.10+, Git, and Codex CLI for `--runtime`. Run from the
repository root:

```bash
python3 spikes/claude-codex-sync/probe.py --runtime
```

Omit `--runtime` for the filesystem-only checks. `results.json` records the
observed run; the `base_commit` of a new run will reflect its own checkout.
The probe exports only tracked instruction, rule, and skill files into a
temporary directory. It constructs a disposable `.agents/skills` directory
containing directory symlinks. The app-server child receives its own temporary
Codex state directory and an environment without inherited API credentials.
The invoking shell's environment is unchanged. User/admin skill discovery may
also occur, so assertions select the six repository-owned skills by name.
Temporary source copies, runtime state, and logs are removed when the probe
finishes successfully.

The only RPC methods invoked are `initialize`, `initialized`, `skills/list`,
and `config/read`. No agent thread or model turn is started.

## What the probe established

| Check | Observed result |
| --- | --- |
| Repeated generation | Identical bytes for identical inputs |
| Source instruction edit | Output changed; stale output was distinguishable |
| Source prompt preservation | Original prompt bytes retained |
| Scoped rule index | 25 files, all 67 listed path patterns retained |
| Generated prompt size | 7,033 bytes, before local/project guidance |
| Existing Codex instructions | Preserved after a replaceable managed block |
| Repeated managed-block update | No duplicate blocks |
| Skill sharing | Six directory symlinks retain original `SKILL.md` bytes |
| Existing unrelated skill path | Collision refused without replacement |
| Private ticket reference | Untracked `reference.md` not exported |
| Real Codex discovery | All six skills found; no parser errors |
| Real Codex refresh | Modified source description visible after `forceReload` |
| Codex config | Disposable config read through `config/read` |

The six skills are `code-review`, `delivery-workflow`, `expand-tool-output`,
`prepare-compaction`, `repository-audit`, and `ticket`. Discovery is not proof
that their Claude-specific model, tool, memory, or connector instructions work
unchanged. The index preserves path strings; it does not implement native
Claude conditional rule injection. A model was not asked to obey the generated
instructions.

## Recommended implementation boundary

Keep `claude/` as the source and introduce a deterministic generator plus a
small, explicit Codex adaptation policy. Produce reviewable output under
`codex/`. Separate generation from installation and preserve existing local
Codex guidance after the generated section. Keep authentication, account state,
local connector values, existing disabled skills, and hook trust state local.

Use an explicit public-file inventory. A private file added inside a skill
directory must not enter generated artifacts or a commit. Public CI can use a
tracked snapshot. Local-only references need their own installation policy;
`ticket/reference.md`, for example, is required at runtime but intentionally
untracked. A bare copy from a public checkout cannot supply that reference.

The actual rules and skills need provider adaptation:

- Resolve model and cross-agent role instructions against the reviewed result
  of issue #121. Do not silently substitute Codex models for Claude roles.
- Preserve rule scopes and instruction precedence. Verify positive and negative
  file-scope examples in a real model turn during implementation.
- Inventory every `settings.json` key and hook as shared, adapted, or excluded
  with a reason. Unexpected keys should require a policy update in CI.
- Do not convert Claude permissions into broader Codex permissions or migrate
  all plugin/connector state by copying local configuration files.
- New or changed hook definitions need Codex's normal trust review. The sync
  must not populate trusted hashes or bypass that review.

## PR automation and local application need separate steps

The target flow is source edit, automatic generation in the same PR,
verification, human merge, local update, then application before a new Codex
session. Generation must be deterministic and expose a non-mutating `--check`.

For same-repository PRs, a bounded workflow can generate files and commit only
its managed output back to the existing PR branch. It must check the expected
head, avoid force pushes, and stop or retry from the new head on races. Use
SHA-pinned actions, narrow write permissions, and a concurrency group. A stale
output check alone does not satisfy automatic generation; committing the
generated update or an explicitly selected equivalent is still required.

Fork/Dependabot PRs require a read-only validation/patch-artifact path. Do not
run untrusted PR code in a privileged `pull_request_target` workflow.

As of the cited GitHub documentation, bot updates using `GITHUB_TOKEN` can
produce approval-required `pull_request` runs, while ordinary `push` runs are
suppressed. Do not assume that a generated commit automatically receives all
required checks. Validate the final generated commit and verify repository
settings/branch protection before selecting the implementation. This spike
did not change workflow permissions, add a GitHub App/PAT, or run remote CI.

Local installation needs backup/restore, dry-run, ownership checks, removal of
only owned stale links, and conflict handling. Integrate with `install.sh`,
`uninstall.sh`, the symlink manifest, and doctor checks. Hook into the local
update operation without replacing existing Git hooks. A GitHub runner cannot
update a Mac's local files by itself, and changing files does not reload the
instructions of an already-running Codex session.

## Next session

1. Read the implementation issue, this file, `results.json`, and repository
   guidance. Refresh related issue #121 and concurrent branches before editing.
2. Claim the implementation issue with the appropriate `agent:*` label and a
   comment identifying the branch/date. The feasibility work does not reserve
   implementation ownership for this session.
3. Use an isolated implementation worktree based on current `origin/main` and
   reproduce this probe. Keep existing uncommitted work outside the change.
4. Implement the generator and adaptation inventory, then the reversible local
   installer, then PR automation. Validate each boundary before live use.
5. Before creating any implementation PR, follow the repository's required
   publication review and user-confirmation process. This spike creates no PR.

## Official references

- [Codex instruction discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
  documents global `AGENTS.md`, precedence, the default 32 KiB project-document
  budget, and startup loading.
- [Codex local skills](https://learn.chatgpt.com/docs/build-skills) documents
  directory-symlink discovery.
- [App-server RPC](https://learn.chatgpt.com/docs/app-server) documents
  `skills/list`, `forceReload`, `config/read`, and external-agent imports.
- [Codex hooks](https://learn.chatgpt.com/docs/hooks) documents trust review for
  each new or changed hook definition.
- [GitHub workflow triggering](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)
  describes `GITHUB_TOKEN` event behavior.
- [GitHub workflow events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
  describes fork and Dependabot token restrictions.
