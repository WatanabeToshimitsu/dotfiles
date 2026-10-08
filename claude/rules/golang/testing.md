---
paths:
  - "**/*.go"
  - "**/go.mod"
  - "**/go.sum"
---
# Go Testing

> This file extends [common/testing.md](../common/testing.md) with Go specific content.

- Use the project's existing `go test` commands and test conventions.
- Start with affected packages; widen the suite when shared changes or failures require it.
- Preserve required race and coverage checks. Run `-race` for changes affecting
  concurrent callers or shared state.
- Measure coverage when the project's checks or the requested change require it.
