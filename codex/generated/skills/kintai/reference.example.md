# Kintai skill reference (template)

Copy this file to `reference.md` next to it and fill in the real values.
`reference.md` is machine-local: it is gitignored and deliberately absent
from `symlink-manifest.sh`, because this repository is public.

## TeamSpirit

- Attendance page: `https://<org>.my.salesforce.com/apex/teamspirit__AtkWorkTimeView`
- Default job: `<job code>` (`<job name>`).
- Other jobs the user sometimes uses: `<job code>` (`<job name>`), or none.
- Commuter allowance: tick every allowance on days whose work location is
  `<location names>`; none on other days.

## Evidence

- Notion timeline view of the user's own tickets, with start and end dates:
  `<view URL>`. A wider view for runs late in the next month: `<view URL>`.
  Open only these views.
- Calendar agenda: `<agenda URL with YYYY/M/D>`. The user's own events read
  `<display name>、承諾` (accepted) or `<display name>、出欠確認が必要` (not
  answered).
- Recurring meetings missing from the calendar: `<name, weekday, time>`, or
  none.
- Events that are not work: `<names or patterns>`.

## Draft

- Directory: `<absolute path>`
- Report style: `<how the user writes a day: ticket line format, meetings,
  reviews, support; a few real example days>`
