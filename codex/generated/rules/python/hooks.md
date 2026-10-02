---
paths:
  - "**/*.py"
  - "**/*.pyi"
---
# Python Hooks

Extend [common/hooks.md](../common/hooks.md).

- Check the effective settings for the event, matcher, and command before treating
  formatting or type checking as automatic.
- Use the project's configured formatter, linter, and type checker for verification.
  This document is not evidence that black, ruff, mypy, or pyright hooks are active.
- Changing global hook configuration is a separate task; a source edit does not
  authorize installing tools or changing the runtime settings.
