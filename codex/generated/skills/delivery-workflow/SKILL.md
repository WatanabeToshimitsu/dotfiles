---
name: delivery-workflow
description: Implement, test, commit, push, or prepare a pull request for a repository change. Use when the user asks to build, fix, refactor, or deliver code.
---

# Delivery Workflow

Scale the process to the change's uncertainty and risk.

1. Inspect repository guidance, relevant code and tests, current branch, and existing worktree changes.
2. Define the smallest coherent change and its verification target.
3. Follow the stage contract below before implementation. For behavior changes, Codex follows RED, GREEN, REFACTOR. Keep refactoring separate from feature behavior.
4. Codex runs focused checks, classifies failures, fixes the cause, and reruns affected checks.
5. Use the `code-review` skill with the independent reviewer assigned by artifact author.
6. Self-review the final diff for scope and accidental changes.
7. After C handback and D, the lead performs authorized Git delivery: stage explicit paths, create logical commits, and use a normal push to the repository's existing remote. Do not force-push, use forced refspecs, mirror remote refs, or delete remote refs. C implementers do not commit or push as part of C.
8. Before creating any PR, including a Draft PR, prepare its exact target, title, body, and complete outgoing commit range. Inspect them for secrets, personal data, and confidential information. Report findings and anything left uninspected. Obtain the user's confirmation immediately before creation. A clean pattern scan is not proof of safety. Do not save permanent PR-creation approval or use another API to evade the confirmation. Create a Draft PR only when one is needed.

Preserve unrelated user changes. Follow the repository's commit and PR conventions. Never add Claude attribution. Do not claim checks passed unless they actually ran; state any verification that could not run.

Ask before committing to product behavior, architecture, data model, compatibility, security, data-loss, or other expensive-to-reverse choices that cannot be resolved from existing evidence.

## Stage contract

This contract applies to both Claude and Codex, including a Codex lead.

| Stage | Owner | Exit evidence |
| --- | --- | --- |
| A: design, policy, acceptance criteria | Claude | Scoped design and acceptance criteria |
| B: review of Claude's design | Independent Codex upper tier, Astra preferred | Findings resolved or stage blocked |
| C: implementation, tests, fixes | Codex, Astra when available | Scoped artifact and actual check results |
| D: review of Codex's implementation | Independent Claude upper tier | Findings resolved or stage blocked |

Compare the artifact author's family with the reviewer's family, regardless of the
coordinator. A Codex lead may dispatch fresh Astra to review a Claude-authored
design; another Codex agent cannot supply stage D. Agent names, changed model
attributes, or an enabled plugin do not establish a cross-family invocation.

Permission boundaries, user changes, repository ownership rules, and existing
Loop stop conditions take precedence. Stage assignments grant no additional
permission to publish, commit, change authentication, or relax sandbox rules.

Tiny tasks may keep read-only exploration and coordination in the current
context. A Codex lead may also implement there. Claude never implements, tests,
or fixes deliverable changes, even mechanical ones. For a tiny change, A may be
Claude-authored acceptance criteria in the authorized claim record. A Codex lead
must obtain A from Claude; its own claim is not A. B may open the C invocation
if that Codex reviewer did not author the design. Resolve B's blocking findings
before C edits. D remains independent. These shortcuts waive neither review.

Risk scales review depth, not the assigned family. Review the coherent final
artifact once per stage, not after every edit. Revisit the affected review when
its findings require changes or later changes invalidate the reviewed artifact
or acceptance criteria. Scope self-checks in step 6 are not independent approval.

### Models and availability

At stage start, check the callable route and current client model support; use
client metadata or provider primary documentation to establish the upper tier.
Record requested model, observed model, and evidence source. Native dispatch
with an explicit model selection is valid client evidence for either family. Otherwise use actual
provider/client metadata when present; JSON need not expose a model field.
Model self-report is never evidence. Missing metadata stays `unknown`.
Codex CLI `-m` is a request only, not observed-model evidence. Without served-model
metadata, record `unknown` and keep B `UNREVIEWED`; native selection evidence remains valid.

If Astra is unavailable in C, keep implementation with an available Codex model
and record the selection and reason. For B or D, use only a verified available
upper-tier model in the required family. If that tier, invocation, or model
evidence is unavailable, mark the stage `UNREVIEWED` and stop; never silently
substitute a lower model or self-review. Record authentication errors and known
usage limits; a successful turn is not a quota audit, and unknown limits remain
unknown. Use the stage call itself as the availability check, avoiding duplicate
model-probe turns. Do not treat a failed sandboxed auth check as proof of no login.
If no Codex model/route can execute C, including auth or quota failures, record C
as `BLOCKED` with the reason and stop. If Claude cannot execute A, do the same for A.
Neither condition permits substituting the other family for the missing author.

### Handoff and exclusive editing

The lead retains the issue label, claim, branch, and dedicated worktree. Each
handoff packet names the inviting lead, owner label, branch, base/ref, and exact
allowed paths. During C only the Codex implementer may edit or run mutating
commands in the claimed worktree and shared deliverable paths; the lead and all
other agents stay read-only there. Private coordination evidence elsewhere and
unrelated worktrees are outside this writer restriction.
Write authority returns to the lead after the implementer's completed or stopped
report. If a crash leaves no report, reclaim it only after runtime/process
evidence confirms the implementer and all spawned write-capable work have stopped,
a read-only worktree/base/allowed-path check is complete, and the lead records C
as stopped. Unknown or orphan writers keep the handoff blocked. Stop on an
out-of-scope request, a changed base/ref, or unlisted worktree changes. Returning
authority does not let a Claude lead implement fixes.
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
requested/observed model and evidence source, author/reviewer role, stage,
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
# B: Codex review outside the repository; packet-only, no edits or tool execution.
rtk proxy codex exec -m gpt-6-astra -C "<packet-dir>" --skip-git-repo-check \
  --ephemeral --sandbox read-only --json \
  --output-last-message "<evidence>/design-review.md" - \
  < "<packet-dir>/packet.md" > "<evidence>/design-review.jsonl"

# C: Codex implementation in the lead's worktree.
rtk proxy codex exec -m gpt-6-astra -C "<worktree>" --sandbox workspace-write \
  --json --output-last-message "<evidence>/implementation.md" - \
  < "<packet-dir>/packet.md" > "<evidence>/implementation.jsonl"

# D: run from the private packet directory; tools, MCP, and browser access disabled.
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

## Codex portability

Preserve the source workflow and publication confirmation. Use native Codex tool names; source tool permissions are not Codex grants. Do not publish or change approval settings merely because this skill is loaded.
