---
paths:
  - "**/*.py"
  - "**/*.pyi"
---
# Python Coding Style

Extend [common/coding-style.md](../common/coding-style.md).

- Follow PEP 8 and the file's existing annotation conventions. Keep public API
  types clear without adding annotations throughout unrelated legacy code.
- Preserve immutable data where callers rely on it; use the existing data model
  instead of introducing dataclasses or named tuples solely from an example.
- Use the project's configured formatter and linter. Do not add black, isort,
  or ruff solely to complete an unrelated edit.
