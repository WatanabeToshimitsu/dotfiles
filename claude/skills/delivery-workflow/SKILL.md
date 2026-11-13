---
name: delivery-workflow
description: Implement, test, commit, push, or prepare a pull request for a repository change. Use when the user asks to build, fix, refactor, deliver code, or plan scheduled or repeated repository work.
---

# Delivery Workflow

Scale the process to the change's uncertainty and risk.
Every lead turn re-reads the whole conversation, so turns cost more as it
grows. Combine independent read-only git checks into one call. Reuse a check
result only while its inputs are unchanged; required HEAD and CI rechecks
still run.

1. Inspect repository guidance, code, tests, branch, and unrelated dirty files.
2. Define the smallest coherent change and its acceptance checks.
   Inspect open PRs for overlapping behavior or files before implementation.
   Report overlapping work and leave it out of the change.
3. Follow the stage contract. Use RED, GREEN, REFACTOR for behavior changes;
   keep refactoring separate from feature behavior.
4. Run focused checks, fix their cause, and rerun affected checks.
5. Use `code-review` for each review the stage contract requires.
6. Self-review the complete final diff for scope and accidental changes.
   Keep related out-of-scope work as proposals instead of implementing it.
   Do not add intermediate variables, conversions, or test cases beyond what
   the requested behavior requires.
7. After C handback and required D, apply the outcomes below before authorized
   Git delivery. Stage explicit files, commit logical units, and push normally.
   Never force-push, use forced refspecs, mirror, or delete remote refs.
   Delegated C implementers do not commit or push.
   After each authorized push, identify CI runs/checks for the repository,
   branch, and exact pushed HEAD. Set a finite watch deadline before starting.
   When a background helper with an explicit smaller model is available, such
   as `general-purpose` with `model: sonnet` in Claude Code, hand it
   `gh pr checks --watch` or `gh run watch <run-id> --exit-status`. It reports
   once on success, failure, timeout, or cancellation, with conclusions, links,
   and failing log excerpts; the lead does not poll it. Otherwise use an
   available background or nonblocking watch; if neither is available, use
   bounded status snapshots.
   Keep the conversation responsive and honor cancellation and Loop stops.
   Recheck the HEAD before reporting, after each new push,
   and after PR creation for PR-triggered CI. Skip monitoring only when CI
   is not configured; an empty check list is not proof of absent CI.
   Report actual conclusions and links without waiting for another request;
   unfinished or unavailable checks remain pending or unknown. Investigate
   failures and report their cause; fixes and re-pushes stay within the
   existing task and delivery authority.
8. When the change alters what a reviewer can see or do in a running web UI,
   run the `evidence-video` skill before drafting the PR, whichever skill
   creates it, and put its Evidence note in the body. Skip docs-only and
   backend-only changes without UI effect. Its login and write approvals still
   apply; record `not run` and the reason in the body when it cannot run.
   Before each PR, including a Draft, prepare its target, title, body, and full
   outgoing commit range. Inspect them for secrets, personal and confidential
   information, and content outside the requested task; report findings and
   uninspected parts. Pattern scans alone do not establish safety. In Claude
   Code, create the PR without separate confirmation when the task includes
   delivery, the inspection is complete, and it finds nothing; ask first when
   findings, uninspected scope, or out-of-scope content remain. In Codex, reuse
   explicit continuing authorization within its stated scope and limits after
   inspection; ask only for missing authorization or remaining inspection concerns.
   One-PR consent never becomes continuing consent. Stop on unresolved sensitive
   findings or runtime rejection, and never evade native checks. Follow the
   [publication guidance](https://github.com/WatanabeToshimitsu/dotfiles/blob/main/docs/pr-approval.md).
   Create a Draft only when needed. After creating a PR, run the `ticket`
   skill's evidence workflow when that skill is available.
9. After live confirmation that this task's PR is merged, clean up only its
   local worktree and branch when cleanup is authorized. Verify their HEAD
   still matches the merged PR HEAD. Keep checkouts with dirty, untracked,
   or ignored files, active writers, shared use, another owner, or unknown
   ownership or activity; report why.
   Use existing cleanup tools only when they preserve these checks, through
   supported managed-worktree archival or non-forced removal. Delete a local
   branch only after it is no longer checked out and `git branch -d` accepts
   it; keep refused branches, including squash/rebase cases.
   Fetch origin and fast-forward only a clean, inactive default-branch
   checkout. Keep missing, dirty, active, or diverged checkouts and report
   why; do not switch, stash, reset, or overwrite them.
   Never delete remote branches. Briefly report removed and retained items.

Preserve unrelated changes and repository conventions. Never add Claude
attribution or report unrun checks as passing. Ask about consequential product,
architecture, data, compatibility, security, or data-loss choices unresolved
by existing evidence.

## Scheduled repository work

For scheduled or repeated work, read [scheduled-work](references/scheduled-work.md).
Build the technical plan from repository evidence; ask only for unresolved
intent, scope, limits, and preferences. Planning authorizes neither activation
nor writes.

## Stage contract

| Stage | Exit evidence |
| --- | --- |
| A: design | Acceptance criteria |
| B: design review | Findings and level |
| C: implementation | Artifact and checks |
| D: implementation review | Findings and level |

D is required for non-obvious changes and changes to hooks, permissions,
settings, sandbox, publication or delivery steps, or secret handling. B runs
when the design has options or touches those areas; resolve its blockers before
dependent C work. Agent instructions (CLAUDE.md, rules, skills, agents) also
need D. Other changes get a full-diff self-review; report B and D as `not run`.
Redo reviews that later changes invalidate.

### Models and availability

Reviewers never helped author the artifact.

| Order | Reviewer |
| --- | --- |
| 1 | Other-family frontier |
| 2 | Same-family non-author frontier, disclosed |

### Review outcomes and continuation

Record B and D apart with requested and observed model; CLI flags and
self-report are not evidence. `PASS` needs a completed frontier review with
blockers resolved; lower-tier or unknown-model advice is `ADVISORY`; an unrun
required review is `UNREVIEWED`. The lead may continue reversible work;
unresolved consequential risk pauses dependent work and delivery.

### Handoff and exclusive editing

A shared worktree has one writer. Reviewers get the full artifact in a private
packet and block on missing evidence. Public summaries list only family, model
evidence, roles, stage, level, relative paths, base/ref, and results.

### Invocation routes

B and D get 600 seconds unless a longer limit is declared first. Read
[invocation](references/invocation.md) for routes and
[recovery](references/recovery.md) on expiry, failure, or a stopped writer.
