---
name: ticket
description: Create and sync work tickets across a team Jira project and a personal Notion staging board. Use when the user starts a work task that should have a ticket, asks to create a ticket, or asks to sync ticket status between Jira and Notion.
---

# Ticket (Jira <-> Notion staging)

The team duplicates tickets between Jira and a shared Notion board that
this skill must never write to. Claude maintains the Jira issues plus a
personal Notion staging mirror; the user copies staging rows to the shared
board manually, about weekly.

`reference.md` sits next to this file and is local-only (untracked). It
holds every concrete identifier: Jira project and board, Notion data
source IDs, workspace names and IDs, shared-board option labels, the
linking-only epic title pattern, and the snapshot query. Read it before
the first Jira or Notion call of a run.

## Systems and workspace mode

- **Jira (writable)**: the project and board named in reference.md, via
  the `atlassian-http` MCP server.
- **Notion shared board (read-only)**: the team board data source in
  reference.md.
- **Notion staging DB (writable)**: "Ticket Staging" in the user's own
  workspace.

The Notion connector binds ONE workspace at a time. Before any Notion
operation, check `notion-fetch self` against the workspace table in
reference.md:

| Connected workspace | Mode                                                                                      |
| ------------------- | ----------------------------------------------------------------------------------------- |
| personal            | normal: staging read/write                                                                |
| shared team         | read-only: search and snapshot only; queue staging writes and ask the user to switch back |

Snapshot of the user's open shared-board tickets:
`~/.claude/ticket/shared-board-snapshot-<date>.csv` (newest wins). Refresh
it whenever the shared workspace happens to be connected (reference.md).

## Entry points

- **Task start (implicit)**: work that warrants a ticket — a feature, fix,
  or investigation with a deliverable — runs the create workflow. Skip
  trivial questions, throwaway experiments, and dotfiles/personal chores.
- **Status change (implicit)**: run the status-change prompt below.
- **Explicit**: `/ticket create`, `/ticket sync`.

## Create workflow

1. Search Jira, the staging DB, and the snapshot CSV for existing tickets;
   search the shared board live only when that workspace is connected.
2. Present plausible candidates. Link to an existing ticket only on user
   confirmation — a false match is worse than a duplicate.
3. Propose compactly (title, type, one-line scope, granularity) and wait
   for approval. Prior in-session agreement on a task breakdown does NOT
   count as ticket-granularity approval: always re-confirm the granularity
   at creation time — session decomposition and ticket granularity are
   different decisions.
4. Create whichever side is missing; Jira first, so the issue key can go on
   the staging row.
5. The full description lives in Jira. The staging page body stays within a
   few blocks; properties carry the rest. Match the language and section
   headings of existing issues in the project.

Epics whose titles match the linking-only pattern in reference.md exist
only to group issues: exclude them from duplicate candidates, sync,
triage, and reports.

## Sync workflow (`/ticket sync` or when asked)

1. Query staging pages where `Sync State != Copied-Done`.
2. Reconcile each with its Jira issue: Jira status changes update staging
   automatically; staging edits by the user (title, estimate, deadline) are
   offered as one batched Jira update, applied on approval.
3. Cleanup: archive `Copied-Done` pages without asking — their content
   survives in Jira and on the shared board (the snapshot covers the lost
   search corpus; do not "fix" this by keeping them). Remind the user to
   empty Notion trash occasionally: the API cannot hard-delete, and trashed
   blocks may still count against the block cap.
4. Triage stale `Not Started` rows (no update for ~6 weeks and low
   priority): propose Not Doing / delete / keep per ticket; apply only what
   the user picks.
5. Report a compact diff of all changes, plus completed-but-uncopied
   tickets as "ready to copy".

## Status-change prompt (automatic)

Whenever a ticket's status changes through this skill — a Jira transition,
a staging update, or tracked work starting or finishing in-session — ask:
「このチケットは共有ボードに提出済み？」

- Yes with URL: set `Shared Board URL`; `Sync State` = Copied, or
  Copied-Done when the ticket is done.
- Yes without URL: `Sync State` = Copied.
- No: leave as is; it stays on the "ready to copy" list.
  Ask once per ticket per status change, not repeatedly in one session.

## Staging schema (summary)

Shared-board-compatible: `Title` (title); `Type`, `Status`, `Priority`,
`Project`, `Section`, `Estimated workload`, `Confidence` (select);
`Deadline` (date). Exact option labels: reference.md — they are the
copy-paste contract with the shared board, keep them identical.
Sync bookkeeping: `Jira Key` (text), `Jira URL` (url), `Shared Board URL`
(url), `Sync State` (select: Draft / Created / Copied / Copied-Done),
`Last Synced` (date).
Status mapping: To Do=Not Started, In Progress=In Progress,
In Review=Reviewing, Done=Complete; record extra project-specific states
in reference.md.

## Hard rules

- NEVER write in the shared team workspace.
- Ticket creation and every Jira write require explicit user approval;
  automatic staging mirror updates and Copied-Done archiving during sync
  are exempt.
- One Jira issue per approved ticket; never bulk-create speculatively.
- Block budget: the staging workspace is on the Free plan (~1000 blocks).
  Keep staging bodies minimal; archive what is done.
- Keep concrete identifiers in reference.md, never in this file: it is
  published in a public repository.
- If searches or MCP calls fail twice, stop and report.
