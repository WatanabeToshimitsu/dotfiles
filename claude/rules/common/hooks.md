---
paths:
  - "**/.claude/**"
---
# Hooks System

Hook events and payload shapes: https://code.claude.com/docs/en/hooks

## Permission Boundary

- Keep security boundaries in Claude Code `permissions.deny` and the Bash sandbox.
- Use PreToolUse hooks only for narrow workflow policy or input normalization.
- Never use the dangerously-skip-permissions flag.
- Review effective rules with `/permissions` and sandbox state with `/sandbox`.
