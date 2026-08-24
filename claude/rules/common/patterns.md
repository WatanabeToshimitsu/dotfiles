---
paths:
  - "**/*.{c,cc,cpp,cs,go,java,js,jsx,kt,kts,php,py,pyi,rb,rs,swift,ts,tsx,vue,svelte}"
---
# Common Patterns

## Skeleton Projects

When implementing new functionality:
1. Search the current repository for an established pattern.
2. Evaluate external skeletons only when the task actually needs a new project or major subsystem.
3. Compare security, maintenance, relevance, and licensing before adoption.
4. Use one focused evaluation by default; add independent reviewers only when the choice is high risk.
5. Adopt or adapt the simplest proven option that fits the requirement.

## Design Patterns

### Repository Pattern

Encapsulate data access behind a consistent interface:
- Define standard operations: findAll, findById, create, update, delete
- Concrete implementations handle storage details (database, API, file, etc.)
- Business logic depends on the abstract interface, not the storage mechanism
- Enables easy swapping of data sources and simplifies testing with mocks

### API Response Format

Use a consistent envelope for all API responses:
- Include a success/status indicator
- Include the data payload (nullable on error)
- Include an error message field (nullable on success)
- Include metadata for paginated responses (total, page, limit)
