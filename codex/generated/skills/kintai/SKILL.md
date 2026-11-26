---
name: kintai
description: Fill a month's TeamSpirit work-hour entries (工数, 作業報告, commuter allowance) from evidence of the work actually done, after the user approves a draft. Use when the user asks to do 勤怠, 工数入力, or the month-end TeamSpirit entries.
---

# Kintai (TeamSpirit month-end entries)

Each workday needs three entries on the TeamSpirit attendance page: hours on a
job (工数), a work report (作業報告), and, on office days, the commuter
allowance (手当). Clock-in and clock-out times are already there; leave them.

`reference.md` next to this file is machine-local: gitignored and absent from
the symlink manifest, because this repository is public. It holds the page
URL, job codes, the allowance rule, the evidence sources, the draft
directory, and the report style. Read it before the first browser call. If it
is missing, create it from `reference.example.md` together with the user.

## Rules

- Write only work that happened. Every report line traces to evidence below.
  Never invent tickets, reviews, or support to fill a day; leave a day
  without evidence blank in the draft, flagged for the user to write.
- Register nothing until the user approves the draft in chat. Approval covers
  the days and values in that draft only.
- Skip non-workdays, days after today, and days that already have hours or
  a report. List every partly filled day for the user: hours without a
  report, a report without hours, or an allowance day without the
  allowance.
- Never press 承認申請 (the monthly submission). It is the user's.
- Do not use a Notion connector for this skill, including its calendar tools:
  the team does not want connectors reading its workspace. Open only the
  Notion views named in reference.md, in Claude in Chrome.

## 1. Read the month

Open the attendance page URL from reference.md in Claude in Chrome. It
redirects to the Visualforce domain, where the page's own JavaScript can be
read. Paste `scripts/teamspirit.js` into one `javascript_tool` call, then
call `ks.month()`. It lists each day of the shown month with its kind, real
work time, work location, saved jobs, allowance count, and report length.
Switch months with the page's `<<前月` and `次月>>` buttons; `ks` survives the
switch, but paste it again after a reload.

Target days: `workDay` true, real work time above 0:00, no saved jobs, no
report, and not after today.

## 2. Gather evidence

- GitHub: run `scripts/gh_activity.py <first day> <last day>` from this
  skill's directory. It prints, per JST day, the PRs the user opened and
  their reviews or comments on others' PRs, leaving out repositories under
  the user's own account.
- Calendar: open the agenda URL from reference.md in Chrome and read it with
  `get_page_text`, one or two weeks per page. Use events the user accepted or
  has not answered, as reference.md describes; skip declined events, all-day
  entries, and events that appear only on other people's calendars. Add the
  recurring meetings reference.md lists.
- Notion: open the timeline view from reference.md, paste
  `scripts/notion_timeline.js` into one `javascript_tool` call, and run
  `await notionTimeline()` in the next. It scrolls the view until every row
  has loaded and returns each ticket's title, start, and end, read from where
  its bar is drawn.
  A ticket without an end date shows only its start day; tickets without a
  start date sit under the view's "No date" count and are not returned. A
  ticket counts as evidence on the days its range covers. Use the titles to
  name the ticket behind a PR (a ticket id in the PR title or branch). If the
  view's relative filter no longer covers the month, use the wider view
  reference.md lists. If it returns `ok: false`, tell the user why and draft
  without ticket dates; never guess them.

## 3. Draft and approval

Write `<draft directory>/<YYYY-MM>-draft.md` (directory from reference.md).
Put the shared values first: job, location and allowance, clock times left
as they are. Then, per target day, a code block holding the exact report
text and one line naming its evidence. Follow the report style in
reference.md. Mark a day without evidence `根拠なし: 自分で書く` and leave its
block empty.

- Job: the default from reference.md. If reference.md lists other jobs, ask
  once which days, if any, go to them.
- Hours: the day's real work time, all on that job.
- Allowance: by the work-location rule in reference.md.

Give the user the draft path, the flagged days, and anything that differs
from the shared values, then wait for an explicit yes. Fill flagged days only
with text the user supplies.

## 4. Register

One `javascript_tool` call per step: a call times out after 45 seconds, and
a loop that outlives it keeps writing with nobody watching.

1. `await ks.fill(date, jobCode, reportText)` opens the 工数 dialog, enters the
   day's real work time on the job and the report, and checks the date,
   time, total, and report length. It cancels the dialog on any mismatch.
2. `await ks.save(date)` presses 登録 on the dialog that step 1 prepared and
   checks that the day now has the entry.
3. On allowance days, `await ks.allowance(date)` then `await ks.save(date)`.

On any `ok: false`, stop. Reload the page, paste `ks` again, check the day
with `ks.day(date)`, and report before doing anything else.

Do the first day alone, reload the page, paste `ks` again, and confirm with
`ks.day(date)` that the entries survived. Then do the rest. At the end,
reload once more and compare every day with the draft: job and time,
allowance count, and report length and line count. Compare lengths, not
text: the tool's output filter blocks some report text.

Report the registered days, the flagged days still open, and that 承認申請 is
left to the user. Close the tabs you opened.

## Codex portability

This skill needs Claude in Chrome, including its JavaScript tool, on the user's signed-in Chrome. In Codex, report it as unavailable; never enter TeamSpirit data with another browser tool.
