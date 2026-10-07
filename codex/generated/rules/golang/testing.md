---
paths:
  - "**/*.go"
  - "**/go.mod"
  - "**/go.sum"
---
# Go Testing

> This file extends [common/testing.md](../common/testing.md) with Go specific content.

## Framework

Use the standard `go test` with **table-driven tests**.

## Race Detection

Run tests with the `-race` flag so data races fail the run:

```bash
go test -race ./...
```

## Coverage

```bash
go test -cover ./...
```
