---
paths:
  - "**/*.py"
  - "**/*.pyi"
---
# Python Patterns

- Preserve existing data models and persistence boundaries. Add a Protocol,
  Repository layer, or DTO only when the requested behavior needs that contract.
- Use context managers for resources that must be released on success and failure.
- Use lazy iteration when the input size or access pattern calls for it; do not
  replace an existing collection API with a generator as unrelated cleanup.
