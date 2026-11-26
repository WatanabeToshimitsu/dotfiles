# Recovery

Read the [stage contract](../SKILL.md#stage-contract) first. This reference
handles writer recovery; it grants no new authority.

## Preserve an available lead

An available frontier lead retains final decisions and checks reviewers'
questions. No frontier lead: save artifact state, actual checks, unresolved
decisions, writer status, and next resumption step, then pause dependent work.
Do not repeatedly ask to downgrade or spend. Quota failure during delegated C
still requires writer recovery before reassignment.

## Recover a stopped writer

A completed or stopped C report returns authority to the lead. Without one:

1. Confirm from runtime/process evidence that C and all spawned write-capable
   work have stopped.
2. Inspect worktree, base/ref, and exact allowed paths read-only.
3. Record C as stopped before reclaiming writer authority.

A timeout or elapsed time alone proves none of these. Unknown or orphan writers
keep the handoff blocked. Do not reassign dependent writes until recovery is
complete. Subsequent fixes remain within the same scope and permissions.

## Keep the handoff durable

The inviting lead retains ownership. Handoff packets name its claim, label,
branch/worktree, base/ref, exact paths, writer status, artifacts, actual checks,
unresolved decisions, and next resumption step.
Private coordination evidence and unrelated worktrees remain outside the
claimed writer scope.

Keep raw packets, outputs, absolute paths, and telemetry private. Public updates
use only the inspected sanitized fields listed in the entry. A blocked handoff
names its missing stage and retains private/public records; its PR remains Draft.
