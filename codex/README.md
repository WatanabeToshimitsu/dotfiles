# Claude to Codex configuration sync

`claude/` remains the source for common instructions, scoped rules and repository
skills. `adaptations.md` records the differences between the two hosts;
`skill-adaptations.json` contains optional skill notes and local references.
Edit those inputs and regenerate; do not hand-edit `generated/`.

Python 3.11 or newer and Git are required. Native discovery tests additionally
require the Codex CLI. macOS and Linux are supported. See [validation results](verification.md) for
the tested versions, evidence and remaining live acceptance steps.

## Edit and verify

```sh
# New source files must be explicitly tracked before they can be exported.
git add claude/rules/new-rule.md
python3 scripts/codex-sync/generate.py --dry-run
python3 scripts/codex-sync/generate.py
python3 scripts/codex-sync/generate.py --check
python3 -B -m unittest discover -s test -p test_codex_sync.py
python3 scripts/codex-sync/probe.py
```

The generator reads only tracked, regular UTF-8 files. Binary resources, input
symlinks and rule frontmatter outside the paths-list format need an explicit
compatibility change. Unsupported skill metadata, tracked private references
and known credential patterns fail validation. The JSON
manifest records source/output hashes and executable flags. Generated resource
scripts keep their Git executable flag; local snapshots restrict access to the
current user. Untracked files are never copied. Only `language` is read from
Claude settings. Other settings, hooks and agent definitions are excluded as
categories; adding or removing them does not require a registration update.

A changed, deleted or unowned generated file blocks regeneration. Reconcile the
edit with the source before trying again. `--check` and `--dry-run` do not modify
files. The manifest detects accidental edits and missing output; it is not a
signed attestation against someone deliberately rewriting both content and
hashes. Pattern scanning supplements the repository's publication review and
does not guarantee that text is safe.

The shared instructions retain the original common text. The rule list in
`AGENTS.md` preserves all patterns and their order without a separate JSON index
or a custom glob matcher. Codex is instructed to read each
matching rule; this is a prompt convention, not Claude's native conditional
loading. Rule files remain byte-identical. Optional skill notes are appended to
the original body; new skills need no annotation entry, and entries for removed
skills are ignored. Changes, additions, deletions and renames propagate through
the generated manifest. Unsupported metadata fails instead of being ignored.

## Apply merged changes on the Mac

After merging the initial implementation and updating the main checkout:

```sh
bash install.sh --codex-only --dry-run
bash install.sh --codex-only

# Future updates fetch main, fast-forward and apply the merged snapshot.
dotfiles-update

# After using plain git pull, apply explicitly.
bash install.sh --codex-only
python3 scripts/codex-sync/install.py check
```

The installer targets the default `~/.codex` profile. `--home` is available for
disposable fixtures; arbitrary `CODEX_HOME` profiles are not synchronized.
Apply requires `main` at the last fetched `origin/main`. It reads committed Git
objects, so private working-tree model preferences and uncommitted source edits
cannot enter the installed snapshot. `dotfiles-update` preserves existing Git
hooks and stops if the merge conflicts. It installs no watcher or scheduled job.
`install.sh --symlinks-only` refreshes an existing Codex sync installation.

The installer creates a private snapshot under `~/.codex/dotfiles-sync/`, then
updates its stable `current` link and owned skill links in `~/.agents/skills/`.
Switching the repository to an implementation branch cannot change the active
snapshot. A managed block is prepended to `~/.codex/AGENTS.md`; existing local
text stays at the end. A nonempty `AGENTS.override.md`, foreign symlink,
same-name skill, edited snapshot or concurrent local edit stops application.
Native disabled skills are not enabled or overwritten. Ambiguous disabled-skill
renames require reconciliation before new names can be enabled.

The ticket skill needs the local `~/.claude/skills/ticket/reference.md`. Its
content is never exported. The installed snapshot links to that local reference;
without it, the skill is reported as unavailable. Project, admin and plugin
skill namespaces remain under the native host's control; duplicate-name checks
cover the two user directories, not every remote plugin catalog.

Start a new Codex task after applying. The existing task's instruction snapshot
does not refresh just because files have changed. `probe.py` checks native skill
discovery, the instruction sources of a new ephemeral thread and untrusted hook
status in a disposable fixture. It makes no model turns and does not prove that
a model will obey every converted instruction. It does not apply to the real
Mac profile or establish that a real GitHub merge has completed.

## Restore and uninstall

```sh
python3 scripts/codex-sync/install.py restore --dry-run
python3 scripts/codex-sync/install.py restore
python3 scripts/codex-sync/install.py uninstall --dry-run
python3 scripts/codex-sync/install.py uninstall
# The repository-wide uninstall also calls the ownership-aware Codex uninstaller.
bash uninstall.sh --dry-run
```

Each mutation writes a private transaction backup. Restore reverses the most
recent transaction and refuses to overwrite later local edits. Uninstall removes
only unchanged owned links and the unchanged shared block; it preserves local
instructions, foreign links, references, snapshots and backups. If instructions
were edited inside the shared block, reconcile them before uninstalling. Retained
backups can contain private local instructions; never commit or upload them.

## PR generation and verification

The read-only preview workflow generates a diff artifact for every PR, including
forks and Dependabot. The existing `validate-configs` job checks committed output.
The publisher workflow runs on `pull_request_target` using the reviewed base
commit, with `contents: write`, `actions: write`, and `pull-requests: read` in its
publisher job only. Those token permissions are repository-wide: path and API
restrictions are enforced by the helper, not by GitHub's token scope. Adding this
workflow to the implementation branch was explicitly approved by the maintainer.

The publisher reads PR blobs as data and never checks out or executes PR code.
It does not consume artifacts or caches from the preview workflow. Only open
same-repository PRs targeting main are eligible; forks and Dependabot remain
read-only. It makes a single-parent commit affecting `codex/generated/` only,
checks the server-advertised head in a temporary pre-push hook, and uses a normal
push. Concurrent updates fail without force-pushing. CI, generator or publication
guard changes require local regeneration and ordinary PR checks.

After pushing, the publisher dispatches read-only CI on the same branch with the
expected SHA. Every CI job rejects a dispatch on a different head. The repository
ruleset checked on 2026-09-11 requires `lint`, `validate-configs` and
`install-ubuntu` from GitHub Actions; keep their names and inspect the checks on
the final generated commit. The workflow does not claim success on their behalf.
GitHub may require approval for bot-triggered PR runs; ordinary bot pushes do not
retrigger push workflows. The explicit dispatch is the final-commit check path.

A post-push API or dispatch failure reports the pushed SHA. To recover, inspect
the current PR head and run CI explicitly for that branch and SHA:

```sh
gh workflow run ci.yml --ref <pr-branch> -f expected_sha=<pushed-sha>
```

A new publisher run on an already generated commit can dispatch CI again without
adding another commit. Rerunning the original event with an obsolete head fails
safely. A branch can still move between dispatch and CI startup; check the actual
head and workflow results before merging. No token scope, branch protection,
review policy, user Git hook or merge setting is changed by the installer.

The first merge bootstraps the publisher. A later, approved representative PR is
required to prove same-PR generation and final-commit checks on GitHub, followed
by a real merged local update and a new Codex task. These live acceptance steps
are not covered by the disposable tests.

## Deliberately native settings

Only the response language becomes a generated instruction. Authentication,
approval rules, sandbox settings, models, reasoning effort, runtime environment,
marketplaces, connectors, plugins and host UI preferences remain native. Claude
hooks and agent definitions are not read or installed into Codex.
Hook trust hashes are never generated or registered. Existing native hook trust
and skill disable settings remain untouched. No per-setting, per-hook or
per-agent exclusion inventory is maintained.

References: [instruction discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md),
[skill discovery](https://learn.chatgpt.com/docs/build-skills),
[native hook trust](https://learn.chatgpt.com/docs/hooks),
[app-server discovery](https://learn.chatgpt.com/docs/app-server),
[GitHub token event behavior](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).
