---
paths:
  - "**/*.test.ts"
  - "**/*.test.tsx"
---

# Testing Guidelines

## Test Structure

- **YOU MUST:** Follow Arrange-Act-Assert pattern
- **YOU MUST:** Use descriptive test names explaining expected behavior
- **YOU MUST:** Keep tests independent and isolated

## Test Organization Order

1. **Basic Rendering** - Initial render verification
2. **Interactions (Normal Cases)** - User interaction and state changes
3. **Error Cases** - Error handling and edge cases

## Reducing Code Redundancy

- When similar patterns frequently occur, utilize common methods or `test.each`
