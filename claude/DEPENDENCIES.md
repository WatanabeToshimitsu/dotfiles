# Claude dependency updates

Runtime dependencies are reviewable in two files:

- `dependencies.lock.json` pins Claude Code diagnostics, the status line package,
  the skills CLI, and every installed skill repository to immutable versions.
- The settings-sourced marketplace in `settings.json` pins every enabled Claude
  plugin to a full 40-character commit SHA without relying on a machine-specific
  filesystem path.

## Update procedure

1. Resolve the candidate release, tag, or commit from the upstream repository.
2. Review the upstream diff from the current lock before changing any pin.
3. Update the relevant lock entry. If a plugin SHA changes, also change the
   marketplace name and the matching keys in `settings.json`. The versioned
   marketplace name forces a fresh cache entry even when an upstream
   `plugin.json` keeps the same semantic version.
4. Run the focused dependency, settings, hook, and macOS smoke tests.
5. Submit the lock change and the reviewed upstream diff in one pull request.

Do not replace a version or commit with `latest`, a floating branch, or an
unqualified repository URL. Skill updates are staged and validated before the
live directories change. A failed install returns a non-zero status, preserves
the previous skills, and does not update `.dotfiles-dependencies.lock.json`.

CI fetches every public pinned source and checks the referenced skill or plugin
entry point. Authenticated plugin sources are skipped in CI and must be verified
manually after GitHub SSH access is configured on a new machine.
