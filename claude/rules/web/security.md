---
paths:
  - "**/{app,pages,routes,controllers,views,handlers}/**"
  - "**/{schema,migrations}/**"
  - "**/*.{sql,tsx,vue,svelte}"
---
# Web Application Security

Applies to code that builds a query, renders untrusted data, or handles a
state-changing request. CORS and JWT belong in `python/fastapi.md`.

## Queries

- Identifiers cannot be parameterized. Map a table name, column name, or sort
  direction through an allowlist before it reaches the query text.
- Raw escape hatches (`queryRaw`, `text()`, `execute`) still take parameters.
  Reaching for raw SQL is not a reason to stop parameterizing.

## Rendering

- `dangerouslySetInnerHTML`, `v-html`, `|safe`, and `mark_safe` need a comment
  at the call site stating why the value is already safe. If it is not, run it
  through a sanitizer.
- Check the scheme against an allowlist before putting user input in a URL,
  `href`, `src`, or event handler attribute.
- Set `Content-Type` explicitly on any response that echoes user-supplied bytes.

## State-changing requests

- Keep the framework's CSRF protection enabled. Exempting a route needs a
  comment at the exemption saying what authenticates the request instead.
- Set session cookies `HttpOnly`, `Secure`, and `SameSite=Lax` or stricter.
