---
name: delivery-workflow
description: Implement, test, commit, push, or prepare a pull request for a repository change. Use when the user asks to build, fix, refactor, deliver code, or plan scheduled or repeated repository work.
---

# Delivery Workflow

Scale the process to the change's uncertainty and risk.

1. Inspect repository guidance, code, tests, branch, and unrelated dirty files.
2. Define the smallest coherent change and its acceptance checks.
   Inspect open PRs for overlapping behavior or files before implementation.
   Report overlapping work and leave it out of the change.
3. Follow the stage contract. Use RED, GREEN, REFACTOR for behavior changes;
   keep refactoring separate from feature behavior.
4. Run focused checks, fix their cause, and rerun affected checks.
5. Use `code-review` with the independent reviewer selected by artifact author.
6. Self-review the complete final diff for scope and accidental changes.
   Keep related out-of-scope work as proposals instead of implementing it.
   Do not add intermediate variables, conversions, or test cases beyond what
   the requested behavior requires.
7. After C handback and D, apply the outcomes below before authorized Git
   delivery. Stage explicit files, commit logical units, and push normally.
   Never force-push, use forced refspecs, mirror, or delete remote refs.
   Delegated C implementers do not commit or push.
   After each authorized push, identify CI runs/checks for the repository,
   branch, and exact pushed HEAD. Watch them through an available background
   or nonblocking call, such as `gh pr checks --watch` or
   `gh run watch <run-id> --exit-status`, with a finite deadline set before
   starting. Keep the conversation responsive and honor cancellation and
   Loop stops; use bounded status snapshots if a nonblocking watch is
   unavailable. Recheck the HEAD before reporting, after each new push,
   and after PR creation for PR-triggered CI. Skip monitoring only when CI
   is not configured; an empty check list is not proof of absent CI.
   Report actual conclusions and links without waiting for another request;
   unfinished or unavailable checks remain pending or unknown. Investigate
   failures and report their cause; fixes and re-pushes stay within the
   existing task and delivery authority.
8. Before each PR, including a Draft, prepare its target, title, body, and full
   outgoing commit range. Inspect them for secrets, personal and confidential
   information; report findings and uninspected parts. Verify explicit human
   approval covers the prepared publication and latest instructions. Reuse it
   within the approved repository, task, content, and limits; multiple PRs need
   explicit multiple, split, or continued PR approval. Ask only for missing or
   expanded authority. Stop on unresolved sensitive findings or runtime rejection;
   uninspected scope needs disclosure and individual approval. Pattern scans alone
   do not establish safety. Never save permanent approval or evade native checks.
   Follow the [publication guidance](https://github.com/WatanabeToshimitsu/dotfiles/blob/main/docs/pr-approval.md).
   Create a Draft only when needed.

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

The configured user-facing frontier leads by default and retains accountability.
Either provider may design and implement. Delegate for tools, capacity, ownership,
or suitability; preserve accepted designs and owners when changing providers.

| Stage | Owner | Exit evidence |
| --- | --- | --- |
| A: design and acceptance criteria | Frontier lead or capable delegate | Scoped design and criteria |
| B: design review | Independent reviewer selected below | Findings disposition and actual level |
| C: implementation, tests, fixes | Lead or capable delegate | Scoped artifact and actual checks |
| D: implementation review | Independent reviewer selected below | Findings disposition and actual level |

Select B from A's author and D from C's author, regardless of coordinator.
Reviewers must not help author the artifact. Self-checks, agent names, model
attributes, and plugin configuration do not prove independent approval or
cross-family invocation. Tiny tasks may put A in the claim and B at the start
of C if B did not author A; neither B nor D is waived.

Permissions, user changes, ownership rules, and Loop stop conditions take
precedence. Stages grant no publishing, authentication, spending, or sandbox
authority. Resolve substantiated blocking B findings before dependent C work.
Review the coherent artifact once per stage; revisit affected reviews when
later changes invalidate the artifact or acceptance criteria.

Give each B and D invocation a wall-clock limit before dispatch: 600 seconds
by default, or a longer finite limit justified by packet size and declared
before the call. Measure from dispatch to the final review; progress does not
extend the deadline. If it expires without a completed review, follow
[stalled-review recovery](references/recovery.md#stop-a-stalled-review).

### Models and availability

Use current client or provider metadata for frontier capability and supported
routes. Fable and Astra are examples, not permanent roles. Keep the configured
lead; never silently downgrade it or ask the user to repeat authorized fallback
choices. Try the actual stage invocation, not duplicate availability probes.

| Order | Fresh reviewer | Outcome |
| --- | --- | --- |
| 1 | Other-family frontier | Independent frontier review |
| 2 | Same-family non-author frontier | Independent frontier review; disclose fallback and shared blind spots |
| 3 | Strongest available non-frontier | Advice for the lead to verify |
| 4 | Lightweight model | Narrow evidence only; never approval |

Report the route and reason. Record requested/observed model and evidence source:
explicit native dispatch is client evidence; otherwise use actual client/provider
metadata. CLI arguments are requests and self-report is never evidence. Missing
metadata stays unknown and cannot establish frontier approval.

**Before retrying or selecting a fallback after quota, route, authentication,
permission, or lead-availability failure, read [recovery](references/recovery.md).**
Do not bypass denials or change authentication, providers, permissions, spending,
credits, or usage resets without separate authority. A sandbox auth failure
does not prove missing login. No frontier lead: save a handoff and pause
dependent work. Never reprobe a known exhausted bucket without reset or new
availability evidence.

### Review outcomes and continuation

Record B and D separately. `PASS` requires completed, verified independent
frontier review and resolution of substantiated blockers. Use `ADVISORY` for
lower-tier or unknown-model findings, `UNREVIEWED` when no review ran. Do not
call same-family review cross-family or advice/no findings frontier approval.

Verify corrections against specifications, reproductions, counterexamples, or
actual checks. Accept supported findings, explain rejected claims, and check
regressions. Do not rewrite correct behavior for unsupported or stylistic
demands. Material uncertainty remains unresolved; unchanged behavior alone
does not dispose of it.

An available frontier lead may continue reversible in-scope preparation,
implementation, and checks with reduced review recorded. Unresolved consequential
design, security, data-loss, or compatibility risks keep dependent work and
delivery paused until the necessary evidence and frontier review are available.
Verified low-impact work may receive authorized delivery with its reduced
review level disclosed. PR confirmation and native boundaries still apply.

### Handoff and exclusive editing

The lead retains claim, label, branch, and worktree. Every C handoff names the
lead, owner, base/ref, and exact allowed paths. C alone may edit or run mutations
in the claimed worktree and deliverable paths; during delegated C everyone else
stays read-only there. Private coordination and unrelated worktrees are outside
this restriction. Stop on out-of-scope requests, moved base, or unlisted changes.
Give C a bounded runtime timeout; fixes require returned authority and the same
scope and permissions.

Authority returns after a completed or stopped C report. **Before reassignment
after a crash, quota failure, timeout, or unknown writer, read
[recovery](references/recovery.md#recover-a-stopped-writer).** Elapsed time alone
does not return authority. Unknown or orphan writers keep the handoff blocked.

Give fresh reviewers only a private packet: purpose, criteria, guidance,
artifact or complete scoped diff, base/ref, allowed paths, actual checks, and
question. Exclude inherited conversation, author verdicts, prior outcomes, and
dirty files. Supply missing evidence or record a blocker; do not repeat
exploration or approve unseen changes. Read-only helpers retain their limits;
implementation needs authorized write tools.

Keep packets, raw output, absolute paths, and telemetry private. Inspect every
public field before posting an authorized sanitized summary: family, requested/
observed model and evidence, author/reviewer roles, stage/level, relative paths,
base/ref, actual results, elapsed time, interventions, and stop reason. Count
human interventions and evidence redispatches separately. Blocked handoffs name
the missing stage and keep PRs Draft. Unrun stages are `not run`; permission
to proceed unreviewed never makes them `PASS`.

### Invocation routes

Prefer a verified native route with explicit model selection and fresh bounded
context. Reviewer packets grant no tool authority; C receives exact paths and
exclusive writer authority. For CLI routes, read the
[shared requirements](references/invocation.md#cli-requirements) and only the
applicable provider/stage section. For native `fable-deep`, read the
[Claude isolation limits](references/invocation.md#claude-review). Configuration
alone proves neither a callable route nor isolation.

## Codex portability

Preserve the source workflow and publication confirmation. Use native Codex tool names; source tool permissions are not Codex grants. Do not publish or change approval settings merely because this skill is loaded.
