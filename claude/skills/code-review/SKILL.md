---
name: code-review
description: Review a code change, branch, commit, or pull request for correctness, regressions, security, and maintainability. Use when asked to review code or before delivering a medium- or high-risk change.
---

# Code Review

Review the coherent final diff after relevant verification has run.

## Depth by risk

- Low risk: targeted tests and self-review.
- Medium risk: one focused Sonnet review.
- High risk: Fable adversarial review; add a specialist only when the risk domain requires one.

Do not start a separate review after every edit. Do not repeat the same exploration in multiple agents.

## Review order

1. Read repository guidance and the full scoped diff.
2. Check changed behavior against the user's request and existing tests.
3. Look for correctness failures, regressions, unsafe input or output handling, concurrency issues, compatibility breaks, and data loss.
4. Verify error handling, secret handling, and boundary validation where relevant.
5. Confirm the reported test and static-check results.
6. Report findings in severity order with precise file locations and consequences.

Treat authentication, authorization, payments, privacy, destructive migrations, cryptography, and externally visible compatibility as high risk.

Do not report style preferences as defects. If no actionable issue remains, say so and state what was verified and what was not.
