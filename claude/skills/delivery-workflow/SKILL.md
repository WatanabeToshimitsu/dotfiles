---
name: delivery-workflow
description: Implement, test, commit, push, or prepare a pull request for a repository change. Use when the user asks to build, fix, refactor, or deliver code.
---

# Delivery Workflow

Scale the process to the change's uncertainty and risk.

1. Inspect repository guidance, relevant code and tests, current branch, and existing worktree changes.
2. Define the smallest coherent change and its verification target.
3. For behavior changes, follow RED, GREEN, REFACTOR. Keep refactoring separate from feature behavior.
4. Run focused checks, classify failures, fix the cause, and rerun affected checks.
5. Use the `code-review` skill at the depth justified by risk.
6. Self-review the final diff for scope and accidental changes.
7. When delivery is authorized, stage explicit paths, create logical commits, and use a normal push to the repository's existing remote. Do not force-push, use forced refspecs, mirror remote refs, or delete remote refs.
8. Before creating any PR, including a Draft PR, prepare its exact target, title, body, and complete outgoing commit range. Inspect them for secrets, personal data, and confidential information; report findings and anything uninspected. Obtain the user's confirmation immediately before creation. A clean pattern scan is not proof of safety. Do not save permanent PR-creation approval or use another API to evade the confirmation.

Preserve unrelated user changes. Follow the repository's commit and PR conventions. Never add Claude attribution. Do not claim checks passed unless they actually ran; state any verification that could not run.

Ask before committing to product behavior, architecture, data model, compatibility, security, data-loss, or other expensive-to-reverse choices that cannot be resolved from existing evidence.
