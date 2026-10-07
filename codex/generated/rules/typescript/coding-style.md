---
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
---
# TypeScript/JavaScript Coding Style

Extend [common/coding-style.md](../common/coding-style.md) and follow the project's
existing type, validation, error-handling, and logging conventions.

- Keep parameter and return types explicit on exported functions, shared utilities,
  and public methods; infer obvious local types.
- Give repeated data shapes and component props named types. Use interfaces for
  extensible object contracts and type aliases for unions or composed types.
- Narrow external input from `unknown`; use generics when the caller determines
  the type. Follow [type-safety.md](type-safety.md) for `any` and strict settings.
- Type callback props explicitly. Use `React.FC` only when the project needs it.
- In JavaScript, keep useful JSDoc consistent with runtime behavior.
- Preserve immutable updates where shared state depends on them.
- Propagate failures through the existing error contract; do not silently swallow
  them or lose diagnostic context when narrowing unknown errors.
- Validate boundary input with the project's existing validator and schemas.
- Use existing production logging; remove debugging output before delivery.
