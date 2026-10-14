---
name: ticket
description: Create work tickets on a team Jira project and a team Notion board, and attach pull requests to them as evidence. Use when the user starts a work task that should have a ticket, asks to create a ticket, or creates a pull request for work linked to a ticket.
---

# Ticket (Jira + team Notion board)

Tickets live in two places: a team Jira project and a team Notion board.
Claude writes both directly. Jira goes through the `atlassian-http` MCP
server. The Notion board goes only through `ticket-browser`, which works
only on the pages a task needs and undoes any other page it reaches. It
cannot stop such a page from loading; the user accepted that until the
browser's own domain limit works on Notion. Never use a Notion connector
for the team workspace: the team's concern is connectors bulk-reading
every ticket on the board.

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
- `ticket-browser` opens only registered pages, runs every other command
  except `get url` and `close` only on one, and after each command goes
  back from any unregistered page. It cannot stop a page from loading; it
  undoes the visit. Register with `ticket-browser allow <url>` only the
  board view URL from reference.md, a ticket the user named, or a
  `ticketUrl` from branch configuration (the user recorded it). A ticket
  this skill creates is registered by `ticket-browser expect-new` (create
  step 5). No workspace search, sidebar, linked pages, or other views.
- Before each command the launcher closes every tab but the one it works
  in; do not keep other pages open in the ticket window.
- Screenshots also capture the sidebar's recent pages; prefer
  `snapshot -s <selector>` and screenshot only to check layout.
- On board views, locate the elements you need with `find role ...` or
  `find text ...` instead of snapshotting the whole view.
- Press only plain editing and navigation keys: Enter, Escape, Tab,
  Backspace, Delete, Home, End, and the arrows.
- Write Notion page text with `click` then `type`: `fill` changes the
  screen but Notion does not save it; keep `fill` for plain inputs such as
  the board's search box. Text starting with `-` and a letter or digit is
  refused as an option. To replace text, click it, press End, and
  Backspace over it first. `Home` and `End` move within one visual line,
  so press ArrowUp before Home and ArrowDown before End on wrapped blocks.
  A leading `- ` makes a bullet. Type a space after a URL so Notion turns
  it into a link; Markdown link syntax stays plain text. To delete the
  current block, press Escape then Backspace. Do not type `@`, `[[`, or a
  leading `/` into Notion: they open page search and block menus.
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
   own search with the task's keywords and the Jira number, and keep only
   result titles that contain the keyword; the search also matches page
   bodies, so the raw result lists unrelated tickets.
2. Present plausible candidates. Link to an existing ticket only on user
   confirmation — a false match is worse than a duplicate.
3. Propose compactly (title, type, one-line scope, granularity) following
   "Granularity and body" below, and wait for approval. Prior in-session
   agreement on a task breakdown does NOT count as ticket-granularity
   approval: always re-confirm the granularity at creation time — session
   decomposition and ticket granularity are different decisions.
4. Reuse whichever side step 2 confirmed and create only what is
   missing. Create the Jira issue first when reference.md says the
   template wants one, with only the fields reference.md lists.
5. Create the board page from the template reference.md names for this
   kind of work, or the default template. Picking a template creates the
   page at once, so run `ticket-browser expect-new` right before clicking
   the template: it registers the one new page the click opens. If the
   board opens new pages in full instead of as a peek, the launcher goes
   back and names the URL; confirm it with the user, `allow` it, and
   continue with that page instead of creating another. Then read the URL
   with `get url`, open the page by itself, set the title first, and fill
   the properties and the template's sections. Title: `<Jira number>. <title>`
   when a Jira issue exists (the digits of the issue key), otherwise
   `X. <title>`. When a Jira issue is added later, rewrite the `X.` prefix.
6. If a step fails, report what already exists: the Jira issue key, the
   board page URL, or both. The next create run reuses them and creates
   only what is missing; never create a second Jira issue or board page.
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
2. Board: open only that ticket URL. Unless the evidence field already
   has a link whose target is the pull request URL, append it on its own
   line as reference.md describes, typing a space after the URL so Notion
   turns it into a link. If the URL is there as plain text, instead of
   appending, Backspace over it and retype it the same way, or delete the
   block when the URL is all it holds. Read the field back and confirm one
   link whose target is exactly the pull request URL.
3. Jira: if `ticketJiraKey` is set, read the issue. Unless the pull
   request is already under the pull request heading reference.md names
   in the link form it gives, append it in that form, or rewrite a bare
   URL into it. A text match cannot tell the two apart, because the link
   form contains the URL. Read the description back and confirm the link
   form, not a bare URL.
4. Steps 2 and 3 are independent: run both even when one finds the link
   already there, so a rerun completes a half-finished append. Neither
   needs approval: the user asked for evidence to be automatic.
5. If either side is unavailable, report which one, the ticket URL or
   issue key, and the text to paste instead of skipping silently.

## Status

When work on a linked ticket starts, set the board status to the "in
progress" value without asking, and propose the matching Jira transition
in the same message. Propose every other status change, on the board or
in Jira, together with the Jira update and apply it on approval.
Use the status buttons reference.md lists when the template has them.

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
- The acceptance section (`完了条件` / `受入条件`) lists the resulting
  states, each about the size of a ticket title one level down. No mechanisms, file names, or commands. For test
  work, phrase each as "a test exists that confirms ...", otherwise the
  ticket reads like feature development.
- Constraints are not target states. Write them as "when doing X, ensure
  Y; if Y cannot hold, do not do X" in the section the template provides
  for notes.
- Self-contained: no section numbers of external documents, and no
  shorthand that exists only in local working notes (plan files, internal
  path IDs). Use terms the team shares: product screens, user jobs,
  systems.
- Merge tickets whose real work is a single small act (asking someone
  for an account, registering it) into the ticket that consumes them.
- Titles name the resulting thing plainly; avoid words that suggest a
  different kind of work (e.g. "データの整備" reads as data upload).
- Write in the language of existing tickets (currently Japanese) and use
  the headings of the template and of the Jira description in
  reference.md, nothing else. One line per bullet.

## Hard rules

- The team Notion workspace is reached only through `ticket-browser` and
  only on the pages listed under "Browser rules".
- Ticket creation and every Jira write require explicit user approval,
  including Jira transitions at the start of work. Exempt: the evidence
  append on the board and in Jira, and the board's start-of-work status.
- One Jira issue per approved ticket; never bulk-create speculatively.
- Keep concrete identifiers in reference.md, never in this file: it is
  published in a public repository.
- If searches or MCP calls fail twice, stop and report.

## Codex portability

Read the machine-local reference.md next to this installed skill before the first Jira or browser call. Its absence makes the skill unavailable. Use the equivalent installed Jira connector only if available and authorized, and reach the Notion board only through `ticket-browser`; do not invent server names, URLs, or workspace IDs.
