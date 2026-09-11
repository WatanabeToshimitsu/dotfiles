---
name: code-review
description: Review a design, code change, branch, commit, or pull request for correctness, regressions, security, and maintainability. Use for design review, when asked to review code, or before delivering any change, including low-risk changes.
---

# Code Review

Review the coherent final diff after relevant verification has run.

## Reviewer by author

- Claude-authored designs require an independent Codex upper-tier reviewer.
- Codex-authored implementations require an independent Claude upper-tier reviewer.
- Use a fresh context that did not produce the artifact. The coordinator's family does not determine the reviewer.
- Scale depth by risk; high-risk changes receive adversarial focus and a specialist only when the domain requires one. Self-checks never replace independent approval.

The [delivery stage contract](../delivery-workflow/SKILL.md#stage-contract) defines models, fallback, tiny-task precedence, invocation, and handoff records. Read it before dispatch. Pass purpose, acceptance criteria, relevant guidance, the artifact, and actual verification results; exclude author verdicts, prior review outcomes, and unrelated user changes.

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

## Codex portability

Fable and Sonnet name Claude reviewers. Use the required provider/model when available. If unavailable, mark that review incomplete; do not label a Codex self-review as a Claude review. Follow the source workflow for roles and local Codex instructions for actual callable tools.
