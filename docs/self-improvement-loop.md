# Bounded self-improvement loop

This experimental workflow combines a native goal with a small repair supervisor.
The goal owns discovery, independent review and GitHub delivery. The Python
supervisor alone does not discover issues, authorize publication or prove a PR
is ready. It returns `awaiting_review`, never a successful-delivery verdict.

## Authority and ownership

Use the current user's explicit authority for this repository and task. Neither
this document nor a contract file grants permission to publish, spend, change
authentication, bypass a native denial, or activate a schedule. Confirm the
existing model route and billing scope before starting a real model call. Do not
allowlist the supervisor to bypass a blocked operation.

Read repository instructions and follow
[delivery-workflow](../claude/skills/delivery-workflow/SKILL.md). The native
frontier lead owns the claim, worktree, acceptance criteria and publication.
A fresh reviewer reviews the design at B. The delegated C worker is instructed
to return text-only edits without tools, Git writes or publication. After C hands back,
a fresh non-author reviewer performs D. The lead inspects the complete outgoing
range and public fields before normal signed commit, push and PR creation.

## One goal activation

Use the following as a task template, filling in the authority and durable
private location from the actual user request:

> Complete one bounded repair in this repository using the current instructions,
> delivery-workflow and self-improvement-run.py. Read the durable handoff first.
> Select one unresolved failure from current CI, issues or verified task logs.
> Check related open and closed PRs, remote branches, recent commits and ownership;
> claim it before editing. Preserve unrelated work.
>
> Pin an isolated worktree, source evidence and acceptance criteria. Add a narrow
> protected regression test and obtain independent B review. Create the private
> contract below and invoke the repair supervisor once. A repair result must
> include the expected baseline failure and passing regression checks.
>
> On awaiting_review, obtain independent D review. Independently confirm the
> regression fails on the pinned baseline and passes on the candidate; do not
> rely on the patch worker's prose. Inspect all outgoing changes, then use normal
> native tools for authorized signed commit/push and inspected PR creation.
> Observe CI for the exact published HEAD with a finite deadline. Unknown checks,
> a Draft PR, or model self-report do not establish completion.
>
> Do not silently retry a terminal or orphaned run, change its budgets, erase
> state, reset its worktree or start another provider after a native denial.
> Report the stop reason and concrete resumption step. Keep private evidence
> outside worktrees, temporary folders and public commits. Save and read back the
> handoff at milestones. Record manual interventions and their causes.

A user should not need another continue message between these stages. Native
permission rejection, missing authority, uncertain ownership or unmet review
gates still stop the dependent stage.

## Private contract

The caller supplies a trusted JSON object. `null` means there is no candidate.
Do not derive command arguments or authority directly from issue text.

| Field | Meaning |
| --- | --- |
| `version` | `1` |
| `case_id`, `source` | Stable case name and source identifier; repository plus source is the duplicate key |
| `repository` | GitHub owner/repository matching origin |
| `worktree`, `branch`, `baseline` | Absolute isolated worktree, branch and exact 40-character base SHA |
| `authority` | Actual user approval basis and allowed actions/data/providers |
| `duplicate_check` | Current remote issue/PR/branch inspection evidence |
| `editable` | Exact existing source files the worker may propose editing |
| `inputs` | Repository-relative source and protected test paths mapped to their initial SHA-256 |
| `reproduce` | Trusted argv array; exit 1 plus the declared marker must establish the expected RED |
| `red_marker` | Specific assertion text distinguishing the regression from an environment error |
| `verify` | Nonempty list of trusted argv arrays for existing regression checks |
| `seconds`, `max_attempts` | Positive repair deadline and patch-proposal cap; each proposal uses one native turn |
| `model` | Currently verified native route `gpt-6-astra` with the OpenAI provider |

Use regular files without symlink components. Editable source must match the
pinned base. Only declared protected input files may initially differ. The
runner rejects staged or unrelated changes. Keep tests out of `editable`.
Every editable file must be in `inputs`, with at least one additional protected
input that the worker cannot edit.

Use a private state directory outside the primary checkout, worktree and
temporary directories. It must belong to the current user and have no group or
other access. For example, use a user-approved persistent task-artifact folder.

```sh
rtk proxy python3 -B /absolute/repository/scripts/self-improvement-run.py \
  --contract /absolute/private-task/case.json \
  --state-dir /absolute/private-task/runs
```

The command executes trusted checks and may invoke the existing Codex CLI's
stdio app-server. Before a model turn, the same client must report ChatGPT
authentication, ordinary usage allowed, no credits or unlimited credits, and
no reached spend or rate limit. Missing or incompatible metadata stops the run
as `billing_unconfirmed`. API-key and base-URL environment overrides also stop
the worker. These are runtime eligibility checks, not a billing receipt or
authorization to change account settings.

Inspect the contract before running it. Do not put `gh`, Docker, service writes,
package installation or unreviewed command strings behind this helper. Use the
native host's authorized tools for GitHub operations. A command manifest is an
execution plan, not a sandbox.

## What the supervisor enforces

- A lock and stable source identity prevent concurrent or duplicate execution.
  Existing terminal state is reported as duplicate. Corrupt or unfinished state
  means ownership is unknown and never grants a fresh attempt.
- Attempts are written before each model invocation. Verification failures may
  consume the remaining declared attempts; native errors and permission denials
  do not trigger another call. Changing branch or budget does not reset a case.
- The worker runs in an ephemeral read-only native thread and is instructed not
  to use tools. The adapter checks the effective model, provider and sandbox,
  binds events to the native thread and turn, and stops on observed tool use,
  approval requests, protocol errors or incomplete turns. It does not remove
  configured MCP servers or provide a technical tool-isolation boundary.
  Observing a tool call cannot undo an external side effect; only cooperative,
  trusted repair tasks belong in this workflow.
- Proposals contain unique literal replacements in exact allowed source paths.
  All edits are validated before writes; protected inputs are checked again
  after execution. The proposer cannot change the declared check commands.
- Baseline exit zero is unreproduced. An unexpected error is not RED. The same
  regression and declared checks must pass before awaiting_review.
- A separate watchdog enforces both wall-clock and monotonic cutoffs for each
  controlled child group. A pipe detects launcher death. TERM, bounded waiting,
  KILL and reaping also clean remaining same-group children after normal exit.
  An unconfirmed cleanup stays unknown; it is never a successful stop.
  POSIX process inspection with `ps` is required and checked before launch;
  a host that denies it cannot establish this cleanup guarantee.
- Atomic journals retain the controller and contract digests, input hashes,
  attempts, deadlines, native model and billing metadata, events, output paths
  and stop reasons. Account email and account response bodies are not retained.

The hard watchdog covers repair/check subprocesses, not the long-lived native
goal process or cancellation of a remote GitHub transaction. B and D need their
own finite supervised invocation limits; CI observation also needs a deadline.
Host crash or killing the watchdog itself can leave unknown state. Reconcile
actual processes and ownership before resuming. Do not edit the journal to
manufacture a clean start.

The supervisor is not an adversarial agent sandbox or a protected L2 grader.
Fixed check commands execute candidate code under the caller's existing runtime
authority. Independent inspection and normal native controls remain necessary.

## Evidence and CI

```sh
rtk proxy python3 -B -m unittest discover -s test -p test_self_improvement_run.py
```

These tests use fake model responses and real local subprocesses. They verify
controller decisions, budgets and process cleanup without credentials or model
calls. They do not prove native model repair quality, permission enforcement or
successful publication.

For every actual pilot retain the original SHA and source evidence, protected
RED/GREEN output, complete diff, A/B/C/D authors and reviewers, actual model
metadata, exact published SHA and CI readback, elapsed time, intervention count
and stop reason. Re-run the proposed regression against the baseline when
accepting a real repair. Verify installed hook paths are separate from the
candidate worktree before editing hook sources.

The native lifecycle and notification protocol are documented in the
[Codex app-server reference](https://learn.chatgpt.com/docs/app-server).
Protocol behavior must also be checked against the installed client's generated
schema and actual responses. A configured model name or a model's self-report
does not establish the effective route. Keep native permissions, authentication,
hooks and account settings intact.

