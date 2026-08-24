# Development Workflow

Scale the workflow to the task's uncertainty and risk. Do not turn every change into a ceremony or a sequence of user prompts.

## Default Autonomous Loop

When the goal is clear and the actions are reversible and in scope, continue through the natural sequence without waiting for repeated instructions:

1. Inspect the relevant code, tests, repository guidance, and current diff.
2. Research external APIs or unfamiliar behavior only when local evidence is insufficient; prefer primary, version-specific sources.
3. Identify the smallest coherent change and its verification target.
4. Follow TDD: RED, GREEN, then REFACTOR. Keep refactoring separate from feature behavior.
5. Run focused checks, fix failures, and repeat until the scoped verification passes.
6. Apply the risk-based review policy from `code-review.md`.
7. Self-review the final diff for scope, correctness, and accidental changes.
8. If the user's request and repository permissions include delivery, create logical commits, push, and open a Draft PR using the repository template.

## Planning Depth

- Small, clear change: keep the plan in the current context and start.
- Multi-file or uncertain change: write a concise plan with dependencies, risks, and verification.
- Product behavior, architecture, data model, compatibility, security, data-loss risk, or expensive-to-reverse decisions: ask one question at a time, with a recommendation and reason, before committing to that branch of the design.

Do not create PRDs, architecture documents, or task lists unless they help the current work or the user requested them.

## Research and Reuse

Search the repository first. Check library documentation, package registries, or existing implementations when dependency behavior is uncertain or reuse is likely to be materially better. Avoid broad web and GitHub searches for routine changes already covered by local patterns.

## Completion

Do not claim completion until the relevant tests and checks have actually run, or clearly state what could not be run. Treat existing unrelated failures and user-owned worktree changes as boundaries, not as permission to expand scope.
