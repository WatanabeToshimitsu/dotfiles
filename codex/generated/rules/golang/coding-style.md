---
paths:
  - "**/*.go"
  - "**/go.mod"
  - "**/go.sum"
---
# Go Coding Style

> This file extends [common/coding-style.md](../common/coding-style.md) with Go specific content.

- Use the project's configured formatter; fall back to `gofmt` when none is configured.
- Use `goimports` only when the project already uses it.
- Wrap errors when adding useful context, using `%w` to preserve the cause.
