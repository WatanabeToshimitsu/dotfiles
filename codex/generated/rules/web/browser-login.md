---
paths:
  - "**/*.{astro,html,jsx,svelte,tsx,vue}"
---
# Browser Login

Applies when agent-browser needs to sign in to an app under verification.

Name one key per app and environment: `<owner>-<repo>` from the `origin`
remote, plus `-<environment>` for a deployed environment. Pass `--restore <key>`
on every command from the first one, so the login survives browser restarts and
is shared across sessions and worktrees. If you add it later, the browser
relaunches; reopen the app before signing in.

When a page shows a login form, run `agent-browser auth login <key> --no-navigate`
with the same launch options. It fills the saved profile of that name and
refuses a page outside the profile's origin.

If the profile is missing, the login fails, or the site asks for a second
factor, ask the user to sign in by hand in a headed browser; reopen the app if
adding `--headed` relaunched it. When `agent-browser auth list` has no profile
named `<key>`, also offer this command for next time, with the login page URL
from `agent-browser get url` minus its query:

```bash
op read -n "op://<vault>/<item>/password" | agent-browser auth save <key> --url <login URL> --username <user> --password-stdin
```

Never type, fill, or print a credential, never run `op` or `auth save` for a
login, and never read files under `~/.agent-browser/`. Keep the key, URLs, and
usernames out of every repository file.
