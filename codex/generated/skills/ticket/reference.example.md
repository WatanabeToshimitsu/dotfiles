# Ticket skill reference (template)

Copy this file to `reference.md` next to it and fill in the real values.
`reference.md` is machine-local: it is gitignored and deliberately absent
from `symlink-manifest.sh`, because this repository is public.

## Jira

- Project `<KEY>`, board `<N>` at
  `<https://<site>.atlassian.net/jira/software/projects/<KEY>/boards/<N>/backlog>`
  via the `atlassian-http` MCP server. Pass `<site>.atlassian.net` as
  `cloudId`.
- Fields the team template asks for, and nothing else: `<fields>`.
- Description headings, and the heading pull request URLs go under:
  `<headings>`.
- When a ticket gets a Jira issue: `<rule from the team template>`.
- Search example:

  ```
  project = <KEY> AND text ~ "<keywords>" ORDER BY updated DESC
  ```

## Notion board

- Board view URL (the only board page to open): `<url>`. Prefer a view
  filtered to the user's own tickets.
- Templates: `<team template name>` for `<kind of work>`; the default
  template otherwise.
- Evidence field: `<property name or body heading>` and how to append.
- Status buttons in the template body, if any: `<start>` / `<review>` /
  `<finish>`.
- Status values: `<not started>` / `<in progress>` / `<reviewing>` /
  `<complete>`, and their Jira counterparts and transition ids.
- Property option labels the skill sets: `<labels>`.

## Team repositories

Repositories whose pull requests should always carry a ticket, by remote
URL: `<remotes>`.

## Linking-only epics

Titles matching `<pattern>` are grouping epics only. Exclude them from
duplicate candidates and reports.
