---
paths:
  - "**/*.test.ts"
  - "**/*.test.tsx"
---

# Testing Guidelines

- Cover changed behavior and failure cases. Check rendering and interactions
  for components; check inputs and results for other targets.
- Keep tests independent, with names describing the expected behavior.
- Reuse setup or `test.each` when cases share the same setup and assertions.
