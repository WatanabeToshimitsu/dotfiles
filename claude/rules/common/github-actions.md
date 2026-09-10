---
paths:
  - ".github/workflows/*.{yml,yaml}"
  - ".github/actions/**/*.{yml,yaml}"
---

# GitHub Actions

## Pinning

- Pin every third-party action to a full commit SHA, never a tag or a branch.
  A tag can be moved to point at other code after review.
- Run `pinact run <workflow>` to pin, and again to refresh; it writes the SHA
  and keeps the version in a trailing comment
  (`uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`).
- `pinact run --check` exits non-zero when something is unpinned. Use it before
  committing a workflow, or as a CI step where the repository wants a guard.
