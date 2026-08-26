# Ticket skill reference (template)

Copy this file to `reference.md` next to it and fill in the real values.
`reference.md` is machine-local: it is gitignored and deliberately absent
from `symlink-manifest.sh`, because this repository is public.

## Systems

- **Jira (writable)**: project `<KEY>`, board `<N>` backlog at
  `<https://<site>.atlassian.net/jira/software/projects/<KEY>/boards/<N>/backlog>`
  via the `atlassian-http` MCP server. Pass `<site>.atlassian.net` as
  `cloudId`.
- **Notion shared board**: `<board name>`, data source
  `collection://<uuid>` (`<shared workspace name>`).
- **Notion staging DB**: "Ticket Staging" in the user's own workspace,
  data source `collection://<uuid>` (database page: `<url>`).

## Workspace table (`notion-fetch self`)

| Connected workspace | ID       | Mode      |
| ------------------- | -------- | --------- |
| `<personal>`        | `<uuid>` | normal    |
| `<shared team>`     | `<uuid>` | read-only |

## Linking-only epics

Titles matching `<pattern>` are grouping epics only — no management
needed. Exclude from duplicate candidates, sync, triage, and reports.

## Shared board option labels (copy-paste contract)

Keep staging select options byte-identical to the shared board's. List
each select property and its exact labels here, including any typos the
shared board actually uses.

- Type / Status / Priority / Estimated workload / Confidence / Section /
  Project: `<labels>`

Record extra tracker workflow states and their transition ids here too,
plus how cancelled or merged-away tickets map onto staging statuses.

## First-run setup

1. Register the Atlassian MCP server as `atlassian-http`.
2. With the personal workspace connected, present the planned database
   name, location, and property list; on approval, create the
   "Ticket Staging" database from the schema summary in SKILL.md plus the
   labels above.
3. Offer to import the newest snapshot CSV as staging rows: properties
   only, no body blocks, `Sync State` = Copied, `Shared Board URL` = the
   row's url. Do NOT create tracker issues for imports; link lazily when
   work on one actually starts.
4. Record the staging data source ID in `reference.md`.

## Snapshot refresh query

When the shared workspace is connected, run via notion-query-data-sources
(SQL mode) and save the result to
`~/.claude/ticket/shared-board-snapshot-<YYYY-MM-DD>.csv`:

```sql
SELECT id, url, Title, Type, Status, Priority, Project, Section, Confidence,
       "Estimated workload", "date:Deadline:start", "Last edited time"
FROM "collection://<shared board uuid>"
WHERE Engineers LIKE '%<user id prefix>%'
  AND Status IN (<open status labels>)
ORDER BY "Last edited time" DESC
```

## Jira search example

```
project = <KEY> AND text ~ "<keywords>" ORDER BY updated DESC
```
