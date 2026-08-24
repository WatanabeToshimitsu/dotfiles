---
paths:
  - "**/*.{c,cc,cpp,cs,go,java,js,jsx,kt,kts,php,py,pyi,rb,rs,swift,ts,tsx,vue,svelte}"
  - "**/*.{json,yaml,yml,toml}"
---
# Security Guidelines

## Mandatory Security Checks

Before ANY commit:
- [ ] No hardcoded secrets (API keys, passwords, tokens)
- [ ] All user inputs validated
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (sanitized HTML)
- [ ] CSRF protection enabled
- [ ] Authentication/authorization verified
- [ ] Rate limiting on all endpoints
- [ ] Error messages don't leak sensitive data

## Secret Management

- NEVER hardcode secrets in source code
- ALWAYS use environment variables or a secret manager
- Validate that required secrets are present at startup
- Rotate any secrets that may have been exposed

## Security Response Protocol

If security issue found:
1. Stop the affected unsafe action and assess severity and scope.
2. Use a security-focused review for high-risk changes or uncertain impact; use Sonnet for bounded checks and Fable / Opus for consequential adversarial review.
3. Fix CRITICAL issues before continuing.
4. Rotate any exposed secrets.
5. Search the relevant boundary for the same issue pattern without expanding into unrelated cleanup.
