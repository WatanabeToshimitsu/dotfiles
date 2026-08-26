# Claude Bash Sandbox Canary

The sandbox is opt-in while compatibility and agent behavior are evaluated. Normal
`claude` sessions keep the existing settings. Start a canary session with:

```bash
claude-sandbox --check
claude-sandbox
```

The launcher loads `~/.claude/sandbox-canary.json` through `--settings`. It requires
Claude Code 2.1.224 or later because that release exposes sandbox violation details
to the model. Versions before 2.1.243 receive a warning because later releases
improve network-violation reporting, but the canary remains available when the
stable update channel has not promoted that release yet.

## Boundary

- The OS sandbox applies to Bash and its child processes. Read, Edit, WebFetch, and
  MCP tools remain governed by Claude Code permissions.
- Bash can write to the working directory, the session temporary directory, and
  explicitly listed package-manager cache directories.
- Common credential files and secret environment variables are unavailable to
  sandboxed Bash commands.
- Unix sockets remain blocked. Local port binding is allowed for development
  servers.
- Common package registries are pre-allowed. Other domains use the normal network
  permission flow because `strictAllowlist` is disabled during the canary.
- Linked Git worktrees use Claude Code's built-in shared `.git` handling. No broad
  home-directory write permission is added.

## Compatibility exceptions

`gh`, `docker`, and `docker-compose` run outside the OS sandbox because of known
macOS TLS and Docker socket incompatibilities. Standard deny and ask rules still
apply before those commands run. Arbitrary `gh api` calls and any
`dangerouslyDisableSandbox` retry require approval.

Run excluded tools as standalone Bash calls. Do not wrap them in a shell loop,
pipeline, command substitution, or conditional: compound commands may not match an
`excludedCommands` entry and can fail with misleading sandbox errors. Prefer a
tool's own waiting command, such as a standalone `gh run watch`, over a shell loop.

## Failure behavior

The canary intentionally uses `failIfUnavailable: false`. Unsupported platforms or
missing dependencies therefore warn and fall back to the normal permission layer
instead of making Claude Code unusable. Runtime sandbox escapes remain available,
but the explicit ask rule makes them visible for approval.

After a sandbox violation, the agent should inspect the reported path or domain and
choose one recovery: request the required permission, request one unsandboxed retry,
or report the blocker. Repeated alternate paths and equivalent command rewrites are
not acceptable recovery behavior.

## Promotion and rollback

Use the behavior-evaluation pilot in issue #38 before moving the `sandbox` block
into the default `settings.json`. Record repeated violations, extra Bash calls,
elapsed time, tokens, and user interventions across representative package-manager,
worktree, GitHub CLI, Docker, and MCP tasks.

The rollback is immediate: exit the canary and start normal `claude`. The canary
does not persist `sandbox.enabled` into the default user settings. Strict settings
such as `failIfUnavailable: true`, `allowUnsandboxedCommands: false`, and
`strictAllowlist: true` should be considered only after the compatibility pilot.
