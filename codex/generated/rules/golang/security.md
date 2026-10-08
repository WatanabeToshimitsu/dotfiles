---
paths:
  - "**/*.go"
  - "**/go.mod"
  - "**/go.sum"
---
# Go Security

Read and follow [common/security.md](../common/security.md) for secret handling,
including required-value validation, alongside this language's rules.

## Security Scanning

Use the project's configured security checks and commands for relevant
changes. Do not add scanners solely for unrelated edits. For security-sensitive
changes, verify coverage; if it is missing or unavailable, report it as
unverified and agree on additional checks before delivery.

## Context & Timeouts

Always use `context.Context` for timeout control:

```go
ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
defer cancel()
```
