---
paths:
  - "**/*.test.ts"
  - "**/*.test.tsx"
---

# Testing Guidelines

## Test Structure

- Follow the Arrange-Act-Assert pattern.
- Use descriptive test names that explain the expected behavior.
- Keep tests independent and isolated.

## Test Organization Order

1. **Basic Rendering** - Initial render verification
2. **Interactions (Normal Cases)** - User interaction and state changes
3. **Error Cases** - Error handling and edge cases

## Reducing Code Redundancy

- When similar patterns frequently occur, utilize common methods or `test.each`
