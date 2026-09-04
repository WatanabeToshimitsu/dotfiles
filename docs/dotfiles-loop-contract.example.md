# Loop contract: one bounded dotfiles delivery

- Status: `example` (copy and approve before use)
- Owner: repository owner
- Approved by: not applicable; this file does not authorize a run
- Last reviewed: 2026-09-04

An approved copy of this example would permit one low-risk Issue to reach a
reviewed pull request. This repository file is illustrative and does not
authorize a scheduled run, automatic merge, or work outside a selected Issue.

## Work to discover and how to select it

- Target work: one open Issue in `WatanabeToshimitsu/dotfiles` that is not an
  epic and has no active owner.
- Discovery source and command: list open GitHub Issues and inspect the selected
  Issue, all matching PRs, matching remote branches, and the latest 15 commits.
- Selection order: `priority:P0`, `priority:P1`, `priority:P2`, then
  `priority:P3`; break ties by unblocking another Issue, then by oldest Issue.
- Maximum work per run: one Issue and one pull request.

## Changes that are allowed

- Allowed paths: only files needed by the selected Issue and named in the claim
  comment before editing.
- Allowed actions: add `agent:codex` or `agent:claude`, leave progress comments,
  create an isolated branch, edit the allowed paths, push that branch, and open
  a pull request.
- Required isolation: use a dedicated worktree based on the latest
  `origin/main`. Never switch or clean another agent's checkout.

## Areas and actions that are forbidden

- Forbidden paths and data: plaintext secrets, credentials, personal data, and
  any unrelated dirty file.
- Forbidden operations: production changes, destructive cleanup, automatic
  merge, bypassing branch protection, or changing the selected Issue's scope.
- Concurrent-work rule: before claiming, check the Issue labels and comments,
  all matching PRs and remote branches, and recent `origin/main` history. Stop
  when another agent has left any active trace.

## Evidence that proves success

- Commands: run the smallest relevant local tests plus the repository's full
  lightweight lint and configuration checks.
- Logs and CI: retain command results in the agent task and require every GitHub
  check on the pull request to pass.
- Artifact: a focused draft pull request that links the Issue, lists
  verification, documents rollback, and has one independent implementation
  review when the governing Issue requires it.

## Stop conditions and budget

- Success: the draft pull request is open, all required checks pass, and required
  review findings are resolved. Merge remains a separate authorized action.
- Timeout: 45 minutes of active work.
- Maximum rounds: three implementation-and-verification rounds.
- Usage ceiling: one Issue, one pull request, three rounds, and no metered
  overage or usage credits. Record any usage figure the runner exposes.
- Stop on risk: a secret or personal-data finding, an overlapping agent claim,
  an unrelated dirty change, ambiguous authorization, or a destructive action.

## Hand work back to a person when

- A product choice, secret access, new external permission, destructive action,
  or scope expansion is needed.
- Tests remain inconclusive after three rounds, the timeout is reached, or the
  branch can no longer be cleanly separated from concurrent work.
- Handoff destination: the selected Issue for scope decisions and its pull
  request for implementation findings.

## Durable state and resumption

- System of record: the selected GitHub Issue and pull request.
- Record after each run: selected Issue, agent label, branch, allowed paths,
  verification, visible usage, current blocker, and exact next action.
- Resume from: reread those records and repeat the concurrent-work checks before
  editing. Do not rely on an earlier session's memory alone.

## Rollback

- Reversible changes: revert the pull request's merge commit, or close the pull
  request before merge.
- State cleanup: if work is abandoned, remove the agent label, close the pull
  request, and delete only the dedicated branch and worktree.
