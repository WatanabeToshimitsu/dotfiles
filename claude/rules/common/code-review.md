# Code Review Standards

## Purpose

Code review ensures quality, security, and maintainability before code is merged. This rule defines when and how to conduct code reviews.

## Review Depth by Risk

- **Low risk**: targeted tests and self review. Examples: local refactors with preserved behavior, documentation, isolated mechanical changes.
- **Medium risk**: one Sonnet focused review after verification. Examples: multi-file behavior changes, non-trivial bug fixes, public API changes with bounded impact.
- **High risk**: Fable / Opus adversarial review after verification. Examples: architecture, concurrency, authentication, authorization, payments, privacy, destructive migrations, compatibility, or data-loss risk.

Do not run a separate agent review after every edit or phase. Review the coherent diff at the point where feedback can still change the result.

## Review Checklist

Before marking code complete:

- [ ] Code is readable and well-named
- [ ] Size and nesting limits met (canonical numbers: coding-style.md Code Quality Checklist)
- [ ] Errors are handled explicitly
- [ ] No hardcoded secrets or credentials
- [ ] No console.log or debug statements
- [ ] Tests exist for new functionality
- [ ] Tests cover the changed behavior and relevant failure modes

## Security Review Triggers

Treat a change as high risk and use a security-focused review when it affects:

- Authentication or authorization code
- User input handling
- Database queries
- File system operations
- External API calls
- Cryptographic operations
- Payment or financial code

## Review Severity Levels

| Level | Meaning | Action |
|-------|---------|--------|
| CRITICAL | Security vulnerability or data loss risk | **BLOCK** - Must fix before merge |
| HIGH | Bug or significant quality issue | **WARN** - Should fix before merge |
| MEDIUM | Maintainability concern | **INFO** - Consider fixing |
| LOW | Style or minor suggestion | **NOTE** - Optional |

## Review Workflow

```
1. Run git diff to understand changes
2. Run the relevant tests and static checks
3. Classify the change as low, medium, or high risk
4. Apply the corresponding self, focused, or adversarial review
5. Re-run affected verification after fixes
```

## Common Issues to Catch

### Security

- Hardcoded credentials (API keys, passwords, tokens)
- SQL injection (string concatenation in queries)
- XSS vulnerabilities (unescaped user input)
- Path traversal (unsanitized file paths)
- CSRF protection missing
- Authentication bypasses

### Code Quality

- Size/nesting over limits (coding-style.md) - split functions, extract modules, use early returns
- Missing error handling - handle explicitly
- Mutation patterns - prefer immutable operations
- Missing tests - add test coverage

### Performance

- N+1 queries - use JOINs or batching
- Missing pagination - add LIMIT to queries
- Unbounded queries - add constraints
- Missing caching - cache expensive operations

## Approval Criteria

- **Approve**: No CRITICAL or HIGH issues
- **Warning**: Only HIGH issues (merge with caution)
- **Block**: CRITICAL issues found

## Integration with Other Rules

This rule works with:

- [testing.md](testing.md) - Test coverage requirements
- [security.md](security.md) - Security checklist
- [git-workflow.md](git-workflow.md) - Commit standards
- [agents.md](agents.md) - Agent delegation
