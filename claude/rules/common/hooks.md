---
paths:
  - "**/.claude/**"
---
# Hooks System

## Hook Types

- **PreToolUse**: Before tool execution (validation, parameter modification)
- **PostToolUse**: After tool execution (auto-format, checks)
- **Stop**: When session ends (final verification)

## Permission Boundary

- Keep security boundaries in Claude Code `permissions.deny` and the Bash sandbox.
- Use PreToolUse hooks only for narrow workflow policy or input normalization.
- Never use the dangerously-skip-permissions flag.
- Review effective rules with `/permissions` and sandbox state with `/sandbox`.

## TodoWrite Best Practices

Use TodoWrite tool to:
- Track progress on multi-step tasks
- Verify understanding of instructions
- Enable real-time steering
- Show granular implementation steps

Todo list reveals:
- Out of order steps
- Missing items
- Extra unnecessary items
- Wrong granularity
- Misinterpreted requirements
