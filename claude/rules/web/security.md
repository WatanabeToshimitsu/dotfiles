---
paths:
  - "**/{app,pages,routes,controllers,views,handlers}/**"
  - "**/{schema,migrations}/**"
  - "**/*.{sql,tsx,vue,svelte}"
---
# Web Application Security

Applies to code that builds a query, renders untrusted data, or handles a
state-changing request. Schema validation belongs in
`typescript/coding-style.md`; CORS, JWT, and rate limiting belong in
`python/fastapi.md`.

## Queries

- Build queries through the ORM or with placeholders. Never concatenate,
  interpolate, or format a value into SQL.
- Identifiers cannot be parameterized. Map a table name, column name, or sort
  direction through an allowlist before it reaches the query text.
- Raw escape hatches (`queryRaw`, `text()`, `execute`) still take parameters.
  Reaching for raw SQL is not a reason to stop parameterizing.

## Rendering

- Leave the template engine's auto-escaping on.
- `dangerouslySetInnerHTML`, `v-html`, `|safe`, and `mark_safe` need a comment
  at the call site stating why the value is already safe. If it is not, run it
  through a sanitizer.
- Check the scheme against an allowlist before putting user input in a URL,
  `href`, `src`, or event handler attribute.
- Set `Content-Type` explicitly on any response that echoes user-supplied bytes.

## State-changing requests

- Keep the framework's CSRF protection enabled. Exempting a route needs a
  comment at the exemption saying what authenticates the request instead.
- `GET` is for reads. A handler that mutates state answers `POST`, `PUT`,
  `PATCH`, or `DELETE`.
- Set session cookies `HttpOnly`, `Secure`, and `SameSite=Lax` or stricter.
