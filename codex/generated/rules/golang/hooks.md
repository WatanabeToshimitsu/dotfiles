---
paths:
  - "**/*.go"
  - "**/go.mod"
  - "**/go.sum"
---
# Go Hooks

Extend [common/hooks.md](../common/hooks.md).

- Check the effective settings for the event, matcher, and command before treating
  formatting or static analysis as automatic.
- Verify with the project's configured tools, such as `gofmt`, `goimports`,
  `go vet`, or `staticcheck` where the project uses them.
- Changing global hook configuration is a separate task; a source edit does not
  authorize installing tools or changing the runtime settings.
