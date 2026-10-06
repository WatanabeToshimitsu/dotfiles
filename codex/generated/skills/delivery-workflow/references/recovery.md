# Recovery

Read the [stage contract](../SKILL.md#stage-contract) first. This reference
handles failed routes and writer recovery; it grants no new authority.

## Classify a failed route

Distinguish exhausted quota, transient rate limits, unavailable routes,
authentication failures, and permission denials. Record model/provider/account
quota scope, failed candidates, and any supplied retry/reset time. Unknown scope
stays unknown; a successful call does not establish remaining quota.

Skip a known depleted shared bucket until reset or new availability evidence.
With unknown scope, try each otherwise eligible alternative at most once per
selection and stop when failure establishes a shared exhausted bucket. Carry
this evidence across stages so the same failure is not probed again.

Honor a supplied transient retry delay for one bounded retry when practical;
do not keep the task in a retry loop. Apply the entry's automatic fallback
without repeated model-choice or confirmation questions. Do not launch every
fallback row merely to satisfy a checklist.

Never change authentication, bypass permission denials, add providers, switch
to paid credentials, enable spending, consume credits or usage resets without
separate authorization. A failed sandbox auth check is not proof of no login.
This procedure creates no waiting automation.

## Preserve an available lead

An available frontier lead retains final decisions and verifies advisory findings.
Record actual B/D levels under the entry's continuation rules. No frontier lead:
save artifact state, actual checks, unresolved decisions, review levels, quota
evidence, writer status, and next resumption step, then pause dependent work.
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
unresolved decisions, review levels, quota evidence, and next resumption step.
Private coordination evidence and unrelated worktrees remain outside the
claimed writer scope.

Keep raw packets, outputs, absolute paths, and telemetry private. Public updates
use only the inspected sanitized fields listed in the entry. A blocked handoff
names its missing stage and retains private/public records; its PR remains Draft.
