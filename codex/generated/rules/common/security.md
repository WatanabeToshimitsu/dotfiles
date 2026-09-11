---
paths:
  - "**/*.{c,cc,cpp,cs,go,java,js,jsx,kt,kts,php,py,pyi,rb,rs,swift,ts,tsx,vue,svelte}"
  - "**/*.{json,yaml,yml,toml}"
---
# Security

## Secrets

- Never hardcode an API key, password, token, or connection string. Read it from
  the environment or a secret manager.
- Never put a real credential in a config file, an example, or a fixture.
- Treat a secret that reached a commit, a log, or a shared channel as exposed.
- Keep sensitive values out of error messages and stack traces.

## When something is found

1. Stop the unsafe action and establish severity and scope before changing anything.
2. Fix critical issues before returning to the original task.
3. Rotate anything exposed.
4. Check the rest of the same boundary for the identical pattern. Do not expand
   into unrelated cleanup.
