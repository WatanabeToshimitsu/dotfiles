# Validation and remaining acceptance work

Historical validation recorded on 2026-09-11 against main `a6813ce`, without applying to the real
Claude/Codex profile. The prior spike at `931d275` was rerun successfully (all
15 checks). Uncommitted preferences in the canonical checkout and the unmerged
work for #121 were not included.

## Reproducible checks

```sh
python3 scripts/codex-sync/generate.py --check
python3 -B -m unittest discover -s test -p test_codex_sync.py
python3 scripts/codex-sync/probe.py
python3 -m unittest discover -s claude/hooks/tests -p 'test_*.py'
python3 -B -m unittest discover -s test -p test_loop_snapshot.py
shellcheck -S warning install.sh uninstall.sh symlink-manifest.sh .shell-utils/dotfiles-update .shell-utils/dotfiles-doctor.sh
actionlint
pinact run --check
git diff --check
```

`test/test-install.sh` intentionally creates and removes fixture dotfiles, so it
replaces HOME with a disposable directory of its own before the first write; the
caller's profile is never touched.

The settings input fingerprint covers a canonical language-only projection, not
the complete Claude settings file. Other input and output hashes keep their coverage.

| Boundary | Evidence |
| --- | --- |
| Public generation | 36 tracked inputs; 34 outputs; 25 rules with all 67 scope patterns; six skills. Only response language is imported from settings; other settings and native runtimes are excluded as categories. Shared AGENTS text is 9,817 bytes before local instructions. |
| Source/output changes | Determinism, add/rename/delete, stale generation, missing output, malformed manifest, executable resources, symlink rejection and private reference exclusion tested. New/removed native settings, hooks and agents require no registration and are not exported. Skill notes are optional and do not block skill removal. |
| Scoped rules | The AGENTS rule list preserves source ordering and patterns, including patterns outside the former custom matcher's subset. There is no separate JSON index or custom matcher. Matching remains a prompt convention, not native conditional injection. |
| Local state | Temporary profiles cover native config/auth/hooks preservation, instruction suffix and override, disabled skills, same-name collisions, absent ticket references, ownership, snapshots, backups, restore/uninstall and failed-write rollback. |
| Concurrent edits | Edits during planning and during the transaction remain intact. Source preferences remain dirty after the update wrapper fetches/fast-forwards the committed snapshot. A pre-existing Git post-merge hook still runs and its bytes stay unchanged. |
| Native Codex | `codex-cli 0.154.0`: nine checks passed. All six skills were discovered without parser errors; a new ephemeral thread listed the installed AGENTS file in `instructionSources`; new/changed hook definitions remained untrusted/modified. Model turns: zero. |
| Existing behavior | 41 hook unit tests and 20 read-only snapshot tests passed. Doctor, hook shell fixtures, external-dependency checks, shellcheck, actionlint and pinact passed. |
| Install/uninstall | Existing manifest-driven install test passed in a temporary macOS HOME and the repository's Ubuntu 22.04 Docker test image. |
| Publication scan | Gitleaks 8.30.1 downloaded from its official release with SHA-256 verification. Directory scan and the repository's synthetic-secret/placeholder fixtures passed. Two initial findings were verified file hashes adjacent to `fastapi` paths; explicit `sha256:` values removed the false positives without adding scanner exclusions. |

After simplification, the sync suite passed all 33 tests on both macOS and Linux/Python 3.11,
and the nine native Codex checks passed again. The disposable image used
for that check was `python:3.11-slim-bookworm` at digest
`sha256:528257d48c1da0dcecc2e725d1ae34498d60c965f1241e39cd6a85a8859bdf84`.
The image receives a read-only worktree mount and no host HOME or credentials.

## Live acceptance remains open

Automatic PR generation and its dedicated CI dispatch have been retired.
[Local generation and ordinary PR checks](README.md#pr-generation-and-verification)
now deliver the generated files. The required `validate-configs` check fails on
stale committed output; the separate read-only preview supplies a diff artifact.
The retired publisher's write permissions and race/API tests are no longer part
of this delivery path. Generation, local ownership, rollback, native-setting and
private-reference protections retain their implementation and fixture coverage.

After an approved human merge, run the local update/apply steps in the main checkout
and start a new Codex task. Applying and restoring the real Mac profile remain
unverified. The fixture confirms instruction-source loading, not model obedience,
conditional-rule semantics or reload of an existing task.

Claude hook/agent runtimes, model selection, permissions, authentication, MCP,
plugins and trust hashes stay native. Binary skill resources, arbitrary local
references, arbitrary CODEX_HOME profiles and unsupported frontmatter need
separate compatibility work. Duplicate-name checks do not cover every project,
administrator or remote-plugin namespace. `ticket` requires its private local
reference and is unavailable without it. No independent final cross-provider
implementation review has been performed.
