---
paths:
  - "**/*.go"
  - "**/go.mod"
  - "**/go.sum"
---
# Go Patterns


- Reuse the project's constructors and dependency boundaries.
- Add interfaces or options only when required by the requested behavior or tests.
- Limit new interfaces to the operations their consumers need.
