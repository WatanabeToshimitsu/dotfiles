---
name: ticket
description: Create work tickets on a team Jira project and a team Notion board, and attach pull requests to them as evidence. Use when the user starts a work task that should have a ticket, asks to create a ticket, or creates a pull request for work linked to a ticket.
---

# Ticket (Jira + team Notion board)

Tickets live in two places: a team Jira project and a team Notion board.
Claude writes both directly. Jira goes through the `atlassian-http` MCP
server. The Notion board goes only through `ticket-browser`, which opens
the pages a task needs and nothing else. Never use a Notion connector for
the team workspace: the team's concern is connectors bulk-reading every
ticket on the board.

`reference.md` sits next to this file and is machine-local: gitignored and
absent from the symlink manifest, because this repository is public. It
holds every concrete identifier: Jira project, board view URL, template
names and when to use each, the evidence field, the Jira fields the team
template asks for, status mapping, team repositories, and the
linking-only epic title pattern. Read it before the first Jira or browser
call of a run. If it is missing, create it from `reference.example.md`
together with the user instead of guessing values.

## Browser rules

- Run every browser command as `ticket-browser <agent-browser args>`.
  Never call `agent-browser` directly for this skill.
- Open only: the board view URL from reference.md, the board's own "New"
  template menu, and ticket pages this skill created or the user named.
  No workspace search, sidebar, linked pages, or other views.
- On board views, locate the elements you need with `find role ...` or
  `find text ...` instead of snapshotting the whole view.
- Press only Enter, Escape, and Tab. Do not type `@`, `[[`, or a leading
  `/` into Notion: they open page search and block menus.
- If a page shows a login screen, ask the user to log in in the
  `ticket-browser` window, then continue.
- If the same browser step fails twice, stop and report.

## Entry points

- **Task start (implicit)**: work that warrants a ticket — a feature, fix,
  or investigation with a deliverable — runs the create workflow. Skip
  trivial questions, throwaway experiments, and dotfiles/personal chores.
- **Pull request created (implicit)**: run the evidence workflow.
- **Explicit**: `/ticket create`, `/ticket link <ticket URL>`,
  `/ticket evidence`.

## Create workflow

1. Search Jira for existing issues. On the board view, use the board's
   own search with the task's keywords and read result titles only.
2. Present plausible candidates. Link to an existing ticket only on user
   confirmation — a false match is worse than a duplicate.
3. Propose compactly (title, type, one-line scope, granularity) following
   "Granularity and body" below, and wait for approval. Prior in-session
   agreement on a task breakdown does NOT count as ticket-granularity
   approval: always re-confirm the granularity at creation time — session
   decomposition and ticket granularity are different decisions.
4. Create the Jira issue first when reference.md says the template wants
   one, with only the fields reference.md lists.
5. Create the board page from the template reference.md names for this
   kind of work, or the default template. Fill the properties and the
   template's sections. Title: `<Jira number>. <title>` when a Jira issue
   exists (the digits of the issue key), otherwise `X. <title>`. When a
   Jira issue is added later, rewrite the `X.` prefix.
6. If the board step fails after the Jira issue exists, report the issue
   key; the next create run finds it in step 1 and finishes the pair.
7. Record the link once work starts on a branch (below).

Epics whose titles match the linking-only pattern in reference.md exist
only to group issues: exclude them from duplicate candidates and reports.

## Links and evidence

The link between work and a ticket is branch configuration in the work's
repository, so it survives sessions and several branches may share one
ticket:

```sh
git config branch.<branch>.ticketUrl <board page URL>
git config branch.<branch>.ticketJiraKey <issue key>
```

Write it when work on a ticket starts on a branch, or on `/ticket link`.

Evidence workflow, after a pull request is created:

1. Read `ticketUrl` for the pull request's head branch. If it is unset,
   ask once which ticket the pull request belongs to when the repository
   is listed as a team repository in reference.md; otherwise stop.
2. Open only that ticket URL. If the pull request URL is already in the
   evidence field, stop.
3. Append the pull request URL to the evidence field reference.md names.
   This needs no approval: the user asked for it to be automatic.
4. If the browser is unavailable, report the ticket URL and the text to
   paste instead of skipping silently.

## Status

When work on a linked ticket starts, set the board status to the "in
progress" value from reference.md without asking. Propose every other
status change, on the board or in Jira, together with the Jira update and
apply it on approval.

## Granularity and body

Tickets describe outcomes; pull requests describe outputs. A ticket is a
state the project or repository will be in, never a list of
implementation steps. If a body reads like a PR description, listing
changes rather than resulting states, the ticket is too fine; several
PRs usually land under one ticket.

- Size: one ticket = one deliverable state a project follower would ask
  about ("is X in place yet?"). Infrastructure for a capability is one
  ticket, not one per component or workflow. Never split by
  implementation phase. INVEST applies, with Valuable weighted over Small.
- `■完了条件` lists the resulting states, each about the size of a ticket
  title one level down. No mechanisms, file names, or commands. For test
  work, phrase each as "a test exists that confirms ...", otherwise the
  ticket reads like feature development.
- Constraints are not target states. Put them under `■注意` as "when
  doing X, ensure Y; if Y cannot hold, do not do X".
- Self-contained: no section numbers of external documents, and no
  shorthand that exists only in local working notes (plan files, internal
  path IDs). Use terms the team shares: product screens, user jobs,
  systems.
- Merge tickets whose real work is a single small act (asking someone
  for an account, registering it) into the ticket that consumes them.
- Titles name the resulting thing plainly; avoid words that suggest a
  different kind of work (e.g. "データの整備" reads as data upload).
- Match the language of existing issues in the project (currently
  Japanese; headings `■背景・目的` / `■完了条件` / optional `■注意`). One
  line per bullet.

## Hard rules

- The team Notion workspace is reached only through `ticket-browser` and
  only on the pages listed under "Browser rules".
- Ticket creation and every Jira write require explicit user approval;
  the evidence append and the start-of-work status are exempt.
- One Jira issue per approved ticket; never bulk-create speculatively.
- Keep concrete identifiers in reference.md, never in this file: it is
  published in a public repository.
- If searches or MCP calls fail twice, stop and report.

## Codex portability

Read the machine-local reference.md next to this installed skill before the first Jira or browser call. Its absence makes the skill unavailable. Use the equivalent installed Jira connector only if available and authorized, and reach the Notion board only through `ticket-browser`; do not invent server names, URLs, or workspace IDs.
