---
name: code-review
description: Review a design, code change, branch, commit, or pull request for correctness, regressions, security, and maintainability. Use for design review, when asked to review code, or before delivering any change, including low-risk changes.
---

# Code Review

Review the coherent final diff after relevant verification has run.

## Reviewer by author

- Review both designs and implementations independently of their author. Either Claude or Codex may have produced either artifact.
- Prefer a frontier reviewer from the other family. Automatically follow the delivery contract's fallback order when unavailable: a fresh same-family frontier, a non-frontier adviser, then bounded lightweight evidence gathering. Do not ask the user to choose again for an authorized fallback.
- Use a fresh context that did not produce the artifact. The coordinator's family does not determine the reviewer. Model names and agent labels alone do not establish a different provider or frontier capability.
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

Each finding needs a violated requirement and reproduction, a counterexample,
or other checkable evidence. Label hypotheses and missing evidence. The frontier
lead verifies findings before accepting changes, records the reason for rejecting
unsupported claims, and checks for regressions after fixes. Preserve existing
behavior when a proposed correction cannot be substantiated; keep material
uncertainty visible rather than treating the claim as resolved.

Treat authentication, authorization, payments, privacy, destructive migrations, cryptography, and externally visible compatibility as high risk.

Do not report style preferences as defects. If no actionable issue remains, say
so and state what was verified and what was not. Record the actual review level
and requested/observed model. Non-frontier advice, unknown model identity, or an
unrun review cannot receive frontier `PASS`; use the delivery contract's outcome
and continuation rules.

## Codex portability

Claude model names require an actual Claude route. Select independent reviewers by artifact author and follow the source workflow's automatic fallback through locally available, authorized tools. A fresh Codex frontier review can be a recorded same-family fallback; never label it a Claude review. Advice, unknown model identity, and self-checks are not frontier approval.
