---
paths:
  - "**/{test,tests,__tests__,spec,specs}/**"
  - "**/*.{test,spec}.{js,jsx,ts,tsx}"
  - "**/test_*.py"
  - "**/*_test.{go,py,rb,rs}"
---
# Testing Requirements

## Test Scope

Follow the repository's existing coverage gates and test conventions. Choose unit, integration, or E2E coverage according to the changed behavior and risk; do not require every test type for every feature.

For bug fixes, first add the smallest regression test that reproduces the reported bug. Do not expand into unrelated cases unless they expose the same root cause and materially reduce recurrence risk.

## Troubleshooting Test Failures

1. Read the failure and identify whether it is caused by the implementation, the test, or the environment.
2. Check test isolation and mocks.
3. Fix the implementation unless the test expectation is demonstrably wrong.

## Test Structure (AAA Pattern)

Prefer Arrange-Act-Assert structure for tests:

```typescript
test('calculates similarity correctly', () => {
  // Arrange
  const vector1 = [1, 0, 0]
  const vector2 = [0, 1, 0]

  // Act
  const similarity = calculateCosineSimilarity(vector1, vector2)

  // Assert
  expect(similarity).toBe(0)
})
```

### Test Naming

Use descriptive names that explain the behavior under test:

```typescript
test('returns empty array when no markets match query', () => {})
test('throws error when API key is missing', () => {})
test('falls back to substring search when Redis is unavailable', () => {})
```
