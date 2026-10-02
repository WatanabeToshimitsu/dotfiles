---
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
---
# TypeScript/JavaScript Testing

Extend [common/testing.md](../common/testing.md).

- Use the project's existing test runner, fixtures, and coverage commands.
- Exercise critical user flows through existing E2E coverage when the changed
  behavior needs it. Do not introduce Playwright or another runner solely because
  a global rule mentions it.
