---
paths:
  - "**/app/**/*.py"
  - "**/fastapi/**/*.py"
  - "**/*_api.py"
---
# FastAPI Rules

Use these rules for FastAPI projects alongside the general Python rules.

## Structure

- Follow the project's app, router, schema, and dependency structure.
- Add factories or layers only when required by the requested behavior.
- Keep database sessions and auth in the project's dependencies; preserve their lifetimes.
- Do not create unmanaged sessions or long-lived clients inside route handlers.

## Async

- Follow the project's sync or async I/O stack.
- Keep blocking database, HTTP, and file operations off the event loop.
- Choose handlers using FastAPI's [sync/async execution rules](https://fastapi.tiangolo.com/async/).

## Schemas

- Never include passwords, password hashes, access tokens, refresh tokens, or internal auth state in response models.
- Validate and filter application responses using the project's `response_model`
  or response-type convention.
- Use field constraints instead of hand-written validation when Pydantic can express the rule.

## Security

- Keep CORS origins environment-specific.
- Do not combine wildcard origins with credentialed CORS.
- Validate JWT expiry, issuer, audience, and algorithm.
- Rate-limit auth and write-heavy endpoints.
- Redact credentials, cookies, authorization headers, and tokens from logs.

## Testing

- Override the exact dependency used by `Depends`.
- Clear `app.dependency_overrides` after tests.
- Use the project's test client and async test conventions.
