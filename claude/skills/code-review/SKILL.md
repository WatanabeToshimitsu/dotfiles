---
name: code-review
description: Review a design, code change, branch, commit, or pull request for correctness, regressions, security, and maintainability. Use for design review, when asked to review code, or before delivering any change, including low-risk changes.
---

# Code Review

Review the coherent final diff after relevant verification has run.

## Review request and target

Treat every review request as fresh. Read the current target and recompute
findings; do not reuse a previous verdict as the result of a new request.
Use the explicit target in the request or arguments. Otherwise, resolve the PR
for the current branch using the available GitHub integration or CLI.
Do not ask when current repository state identifies the target. Ask only when
it remains ambiguous, cannot be determined, or no current-branch PR exists.

## Reviewer by author

For every review task, first read and follow the
[delivery stage contract](../delivery-workflow/SKILL.md#stage-contract).
It defines independent design and implementation review, reviewer selection,
fallback, invocation, handoffs, findings disposition, and review outcomes.

Scale depth by risk; high-risk changes receive adversarial focus and a specialist
only when the domain requires one. Self-checks never replace independent approval.

Do not start a separate review after every edit unless the user explicitly
requests one. Do not repeat the same exploration in multiple agents.

## Review order

1. Read repository guidance and the full scoped diff.
2. Check changed behavior against the user's request and existing tests.
3. Look for correctness failures, regressions, unsafe input or output handling, concurrency issues, compatibility breaks, and data loss.
4. Verify error handling, secret handling, and boundary validation where relevant.
5. Confirm the reported test and static-check results.
6. Report findings in severity order with precise file locations and consequences.

Each finding needs a violated requirement and reproduction, a counterexample,
or other checkable evidence. Label hypotheses and missing evidence.

Treat authentication, authorization, payments, privacy, destructive migrations, cryptography, and externally visible compatibility as high risk.

Do not report style preferences as defects. If no actionable issue remains, say
so and state what was verified and what was not.
