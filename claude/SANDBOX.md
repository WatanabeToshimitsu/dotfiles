# Claude Bash Sandbox Canary

This is a macOS-only, opt-in trial. Normal `claude` sessions do not enable the
sandbox. Start a trial session with:

```bash
claude-sandbox --check
claude-sandbox
```

The launcher loads `~/.claude/sandbox-canary.json` through `--settings`. The local
stable Claude Code 2.1.231 is the tested version. Claude Code 2.1.187 is the minimum
because credential protection is unavailable before that version.

## Boundary

- The OS sandbox applies to Bash and its child processes. Read, Edit, WebFetch, and
  MCP tools remain governed by Claude Code permissions.
- Bash can write to the working directory and Claude Code's session temporary
  directory. Add another path only after an actual task needs it.
- Common credential files and secret environment variables are unavailable to
  sandboxed Bash commands.
- Local port binding remains available for development servers and browser tests.
- No package cache or registry is pre-allowed. A task that needs one uses the
  normal permission flow.

## Compatibility exceptions

`gh`, `docker`, and `docker-compose` run outside the OS sandbox because of known
macOS TLS and Docker socket incompatibilities. Standard deny and ask rules still
apply before those commands run. Arbitrary `gh api` calls and any
`dangerouslyDisableSandbox` retry require approval.

Run excluded tools as standalone Bash calls. Do not wrap them in a shell loop,
pipeline, command substitution, or conditional: compound commands may not match an
`excludedCommands` entry and can fail with misleading sandbox errors. Prefer a
tool's own waiting command, such as a standalone `gh run watch`, over a shell loop.

## When a command is blocked

The canary uses `failIfUnavailable: false`, so a Claude Code runtime failure can
fall back to the normal permission layer. The launcher itself refuses non-macOS
platforms.

After a sandbox violation, the agent should inspect the reported path or domain and
choose one recovery: request the required permission, request one unsandboxed retry,
or report the blocker. Repeated alternate paths and equivalent command rewrites are
not acceptable recovery behavior.

Stop the trial if sandbox handling adds repeated retries or unrelated workaround
commands. Exit the session and start normal `claude`; no setting is promoted to
the default configuration.
