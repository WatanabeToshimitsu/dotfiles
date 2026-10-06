---
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
---
# TypeScript/JavaScript Patterns

- Preserve existing API response contracts, data access boundaries, and component
  patterns when fixing a bug.
- Add an API envelope, custom hook, or Repository abstraction only when the
  requested behavior and existing design justify it.
- Keep runtime validation aligned with public types; a type assertion does not
  validate untrusted data.
