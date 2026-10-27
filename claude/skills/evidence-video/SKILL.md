---
name: evidence-video
description: Record short, human-paced MP4 videos of a web UI change for a pull request's Evidence section, including mocked failure paths. Use when asked to film, record, or capture a verification video of a web app, and before opening a pull request whose change is visible in a running web UI.
---

# Evidence video

Produce one short MP4 per scene that a reviewer can watch once and understand:
a visible pointer, readable pauses, no dead time. Commands and mock code are in
[recording](references/recording.md); read it before the first browser call.

## Required steps

1. **Shot list.** Per scene: the steps, the result that must be visible, and
   the dev writes one take makes. Ask the user once to approve the list and its
   writes. That approval covers the first take of each scene only.
2. **Directories.** Final MP4s go to one deliverable directory outside the
   repository. Raw takes, contact sheets, and frames go to a separate work
   directory; nothing else lands next to the MP4s.
3. **Browser.** Start the dev server with `memgate run -- <dev command>`. Pass
   `--session <name> --headed --idle-timeout 0` on every browser command;
   other launch options relaunch the browser and lose the login. The user logs
   in by hand; never type or store credentials. If waiting for login times
   out, ask again; never close the browser. Keep it open across retakes.
4. **Failure paths.** Mock in the page, for one URL and method, behind a flag,
   with a network abort route on that URL as a guard. Prove the mock with the
   probe in the reference before recording; it never reaches the server.
5. **Record in a subagent** with an explicit model that can run shell commands,
   so the main thread stays readable. Hand it the shot list, approved writes,
   session name, directories, and this skill. It never logs in, never closes the browser, and
   never retakes without the lead.
6. **Take rules.** `record start <raw>.mp4 --cursor`. Move with `get box` then
   `mouse move <x> <y> --duration 600-900 --steps 30-40`; press with
   `mouse down` and `mouse up`. Never `click` while recording; it teleports.
   After each result, park the pointer beside it, not on its text, and hold
   about 1.5 s. If no result appears within 15 s, stop the take and report;
   never press again. A write whose outcome is unknown counts as made.
7. **Trim.** `python3 -I <skill-dir>/scripts/trim_idle.py <raw>.mp4 <final>.mp4`
   keeps 1.2 s of each still stretch. Deliver MP4, not GIF: GitHub plays it
   inline and text stays readable.

## Self-review loop

The subagent checks each trimmed MP4, then the lead checks it again the same
way before reporting; never forward a subagent's claim unverified.

- [ ] The pointer is visible and travels to each control it uses.
- [ ] Every expected state stays on screen for about 1 s or more.
- [ ] Each message reads correctly in a full-resolution frame crop. Snapshots
      taken during recording miss short banners; do not use them as evidence.
- [ ] No still stretch outlasts its reading time; `freezedetect` finds
      candidates, the reading time decides.
- [ ] About 25 s or less per scene.
- [ ] No credentials, tokens, DevTools, request headers, or unrelated personal
      data are on screen.

On a failure, re-edit first. Retake only when content is missing, at most twice
per scene, and only after the user approves that retake and its writes. After
two retakes, report the failure instead.

## Report

Per scene: file path, length, what it shows, the dev writes it made, and how
any failure was mocked. Add one sentence for the PR's Evidence note. Never
upload the videos; the user attaches them, and a PR body never calls
unattached videos attached. When the skill cannot run, report `not run` with
the reason: no reachable environment, no subagent, login not completed, or
writes not approved.

Finally remove the mocks and routes, stop the dev server, and leave the
logged-in browser open until the user says they are done.
