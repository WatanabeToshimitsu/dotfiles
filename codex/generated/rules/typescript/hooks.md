---
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
---
# TypeScript/JavaScript Hooks

Extend [common/hooks.md](../common/hooks.md).

- Check the effective settings for the event, matcher, and command before treating
  formatting, type checking, or console warnings as automatic.
- Use the project's configured formatter and type checker for verification.
- Changing global hook configuration is a separate task; a source edit does not
  authorize installing tools or changing the runtime settings.
