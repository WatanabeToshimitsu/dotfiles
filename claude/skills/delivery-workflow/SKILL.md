---
name: delivery-workflow
description: Implement, test, commit, push, or prepare a pull request for a repository change. Use when the user asks to build, fix, refactor, deliver code, or plan scheduled or repeated repository work.
---

# Delivery Workflow

Scale the process to the change's uncertainty and risk.

1. Inspect repository guidance, relevant code and tests, current branch, and existing worktree changes.
2. Define the smallest coherent change and its verification target.
3. Follow the stage contract below before implementation. For behavior changes, the implementer follows RED, GREEN, REFACTOR. Keep refactoring separate from feature behavior.
4. The implementer runs focused checks, classifies failures, fixes the cause, and reruns affected checks.
5. Use the `code-review` skill with the independent reviewer assigned by artifact author.
6. Self-review the final diff for scope and accidental changes.
7. After C handback and D, apply the review outcome rules below before authorized Git delivery: stage explicit paths, create logical commits, and use a normal push to the repository's existing remote. Do not force-push, use forced refspecs, mirror remote refs, or delete remote refs. Delegated C implementers do not commit or push as part of C.
8. Before creating any PR, including a Draft PR, prepare its exact target, title, body, and complete outgoing commit range. Inspect them for secrets, personal data, and confidential information. Report findings and anything left uninspected. Obtain the user's confirmation immediately before creation. A clean pattern scan is not proof of safety. Do not save permanent PR-creation approval or use another API to evade the confirmation. Create a Draft PR only when one is needed.

Preserve unrelated user changes. Follow the repository's commit and PR conventions. Never add Claude attribution. Do not claim checks passed unless they actually ran; state any verification that could not run.

Ask before committing to product behavior, architecture, data model, compatibility, security, data-loss, or other expensive-to-reverse choices that cannot be resolved from existing evidence.

## Scheduled repository work

When planning or carrying out scheduled or repeated repository work, read
[the scheduled-work reference](references/scheduled-work.md). Prepare the
technical plan from repository evidence; ask the user for unresolved intent,
scope, limits, and preferences. Planning does not authorize activation or writes.

## Stage contract

The user-facing frontier model leads the task by default. Either Claude or Codex
may design, implement, test, and fix through its authorized tools. Delegate for
concrete reasons such as tools, capacity, existing ownership, or demonstrated
suitability. Preserve accepted designs and the task's owner when changing models;
a provider change alone is not a reason to redesign or open a competing task.

| Stage | Owner | Exit evidence |
| --- | --- | --- |
| A: design, policy, acceptance criteria | Frontier lead or capable delegate | Scoped design and acceptance criteria |
| B: design review | Independent reviewer selected below | Findings disposition and actual review level |
| C: implementation, tests, fixes | Lead or capable delegate | Scoped artifact and actual check results |
| D: implementation review | Independent reviewer selected below | Findings disposition and actual review level |

One model may perform A and C. Select B from A's author and D from C's author,
regardless of the coordinator. For example, if an Astra lead delegates C to
Claude, D prefers a fresh Codex frontier reviewer. A reviewer must not have helped
produce the artifact; the lead's self-check is never independent approval.
Agent names, model attributes, or an enabled plugin do not establish an actual
cross-family invocation.

Permission boundaries, user changes, repository ownership rules, and existing
Loop stop conditions take precedence. Stage assignments grant no additional
permission to publish, commit, change authentication, or relax sandbox rules.

Tiny tasks may keep exploration, coordination, and implementation in the current
lead context. A may be concise acceptance criteria in the authorized claim
record. B may open the C invocation if that reviewer did not author A. Resolve
substantiated blocking findings before dependent C edits; apply the continuation
rules below when review is unavailable or advisory. D remains independent. These
shortcuts waive neither review stage nor its evidence record.

Scale review depth by risk. Review the coherent final artifact once per stage,
not after every edit. Revisit the affected review when fixes or later changes
invalidate the reviewed artifact or acceptance criteria.

### Models and availability

Use current client metadata or provider primary documentation to identify
frontier capability and supported routes. Fable and Astra are current examples,
not permanent role assignments. Keep the configured user-facing frontier model;
do not silently replace it with a lower model. Delegation does not change the
lead's responsibility for final decisions.

Record requested model, observed model, and evidence source. Native dispatch
with explicit model selection is valid client evidence. Otherwise use actual
provider/client metadata when present; JSON need not expose a model field.
Model self-report is never evidence. CLI model arguments are requests, not
served-model evidence. Missing metadata stays `unknown` and cannot establish
frontier approval, although the output may supply advisory evidence.

For B and D, automatically select the first available, authorized option:

| Order | Reviewer | Permitted outcome |
| --- | --- | --- |
| 1 | Other-family frontier in a fresh context | Independent frontier review |
| 2 | Same-family frontier in a fresh non-author context | Independent frontier review; record the fallback and shared-model blind spots |
| 3 | Strongest available non-frontier model | Advisory findings for the frontier lead to verify |
| 4 | Lightweight model | Narrow evidence gathering or candidate findings, never approval |

Do not ask the user to repeat the model choice or fallback authorization. Report
the selected route and reason briefly. Use the actual stage invocation as the
availability check; avoid duplicate model-probe turns. Do not launch every row
merely to satisfy a checklist. Read-only helpers keep their existing tool limits;
implementation requires a capable lead or delegate with authorized write tools.

Record exhausted quota scope (model, provider, or account), failed candidates,
and retry/reset time when supplied. Unknown scope and limits remain unknown;
a successful turn is not a quota audit. Skip a known depleted shared bucket
until reset or new availability evidence. For unknown scope, try each otherwise
eligible alternative at most once per selection and stop when the failure
establishes a shared exhausted bucket. Retain this evidence across stages so the
same failure is not probed again without new evidence.

Distinguish exhausted quota from transient rate limiting, unavailable routes,
authentication failures, and permission denials. Honor a supplied retry delay
for a bounded transient retry when practical; do not keep the task in a retry
loop. Never change authentication, bypass permission denials through fallback,
add providers, switch to paid credentials, enable spending, or consume credits
or usage resets without separate authorization. Do not infer no login from a
failed sandboxed auth check. This policy creates no waiting automation.

### Review outcomes and continuation

Record B and D separately. Use `PASS` only for a completed, verified independent
frontier review whose substantiated blocking findings are resolved. Use
`ADVISORY` for lower-tier or unknown-model findings and `UNREVIEWED` when no
independent review ran. A lower-tier report with no findings is not frontier
approval. Never relabel same-family review as cross-family review.

The frontier lead checks each proposed correction against the specification,
reproduction, counterexample, or actual verification results. Accept supported
findings, explain rejected claims, and check for regressions after fixes. Do not
rewrite correct behavior to satisfy unsupported or stylistic demands. An
unverifiable material concern stays unresolved; preserving existing behavior
does not dispose of that concern.

While a frontier lead remains available, reversible in-scope preparation,
implementation, and checks may continue with advisory or missing review recorded.
This exception does not authorize dependent work on unresolved consequential
design choices, security, data-loss, or compatibility risks. Keep those decisions
and their delivery paused until the necessary evidence and frontier review are
available. For low-impact work whose acceptance criteria are verified, authorized
delivery may proceed with the reduced review level explicitly reported; never
claim full approval. PR confirmation and all other publication boundaries remain.

If no frontier can continue as lead, save the artifact state, actual checks,
unresolved decisions, review levels, quota evidence, writer status, and next
resumption step. Pause dependent work without repeatedly asking to downgrade or
spend. A quota failure during delegated C still requires stopped-writer recovery
before reassignment; elapsed time alone does not return writer authority.

### Handoff and exclusive editing

The lead retains the issue label, claim, branch, and dedicated worktree. Each
handoff packet names the inviting lead, owner label, branch, base/ref, and exact
allowed paths. During C only its implementer may edit or run mutating commands
in the claimed worktree and shared deliverable paths. If C is delegated, the
lead and all other agents stay read-only there; if the lead performs C, it is
the sole writer. Private coordination evidence elsewhere and unrelated worktrees
are outside this writer restriction.
Write authority returns to the lead after the implementer's completed or stopped
report. If a crash leaves no report, reclaim it only after runtime/process
evidence confirms the implementer and all spawned write-capable work have stopped,
a read-only worktree/base/allowed-path check is complete, and the lead records C
as stopped. Unknown or orphan writers keep the handoff blocked. Stop on an
out-of-scope request, a changed base/ref, or unlisted worktree changes. Either
lead may implement subsequent fixes after authority has returned, within the
same scope and permissions.
Give C an appropriate bounded runtime timeout. On timeout, use the stopped-writer
recovery above; elapsed time alone does not prove that every writer has stopped.

A reviewer must not have helped produce the artifact. Start a fresh context
with a private packet containing purpose, acceptance criteria, relevant guidance,
artifact or full scoped diff, base/ref, allowed paths, actual verification
results, and the review question. Omit inherited conversation, author verdicts,
prior review outcomes, unrelated changes, and user dirty files. Reviewers use
the packet and report missing evidence; the lead supplies what is needed or
records a blocker. Do not duplicate exploration or approve unseen changes.

Keep packets, raw output, absolute worktree/evidence paths, and telemetry private.
For authorized issue/PR updates, publish only a sanitized summary: family,
requested/observed model and evidence source, author/reviewer role, review level, stage,
repo-relative paths, base/ref, actual result, elapsed time, intervention count,
and stop reason. Check every public field for secrets, personal information,
and local paths before posting. Count human interventions and evidence
redispatches separately. A blocked handoff names the missing stage and retains
these private/public records; any PR remains Draft. Unrun stages are `not run`.
An explicit user decision to proceed unreviewed never turns that stage into PASS.

### Invocation routes

Prefer an available native dispatch with explicit model selection and a fresh,
bounded context. Supply only the packet to reviewers and transfer C's allowed
paths and exclusive writer role to the implementer. Verify the actual callable
route; existing plugin configuration alone is not proof of one.

Native `fable-deep` retains read-only tools: packet-only behavior is a prompt
restriction, not isolation from unrelated files. Prefer the tool-less Claude CLI
route below when tool isolation is needed; read-only tools alone do not enforce it.

CLI alternatives below use private directories and explicit stdin. Replace the
placeholders, check installed CLI support, and retain normal rules, sandbox,
and authentication. These examples are invocation instructions, not run evidence.

```bash
# B or D when Codex is selected; packet-only, no edits or tool execution.
rtk proxy codex exec -m gpt-6-astra -C "<packet-dir>" --skip-git-repo-check \
  --ephemeral --sandbox read-only --json \
  --output-last-message "<evidence>/design-review.md" - \
  < "<packet-dir>/packet.md" > "<evidence>/design-review.jsonl"

# C example when a capable Codex delegate is selected.
rtk proxy codex exec -m gpt-6-astra -C "<worktree>" --sandbox workspace-write \
  --json --output-last-message "<evidence>/implementation.md" - \
  < "<packet-dir>/packet.md" > "<evidence>/implementation.jsonl"

# B or D when Claude is selected; run from the private packet directory.
rtk proxy claude --restricted --tools '' --disallowedTools 'mcp__*' \
  --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
  --disable-slash-commands --no-chrome \
  --no-session-persistence --model fable --effort high --print --output-format json \
  < "<packet-dir>/packet.md" > "<evidence>/implementation-review.json"
```

Apply the stage-specific fallback above if a model is rejected. Do not bypass
sandbox, rules, or user configuration to make a route work. The Codex read-only
sandbox prevents writes, not reads: explicitly instruct the reviewer to use only
the supplied packet and not invoke tools. For Claude, extract model evidence
from `modelUsage` when present; for Codex, use available client metadata or the
native selection record. Keep absent fields unknown rather than inventing them.
