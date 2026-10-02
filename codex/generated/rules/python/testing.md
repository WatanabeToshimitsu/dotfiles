---
paths:
  - "**/*.py"
  - "**/*.pyi"
---
# Python Testing

Extend [common/testing.md](../common/testing.md).

- Keep the project's existing runner and fixture style, including `unittest`.
  Do not migrate a regression test to pytest or add pytest solely from this rule.
- Use existing coverage gates and commands; run the smallest relevant suite first.
- Follow the existing fixture cleanup convention so temporary state is removed
  even when an assertion fails.
