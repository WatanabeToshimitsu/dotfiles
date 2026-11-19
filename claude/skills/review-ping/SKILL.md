---
name: review-ping
description: Register a Slack review request for a pull request once, then send it from the user's own Slack session only after CI passes, so the user can move on right away. Use when the user asks to send, queue, or schedule a Slack review request, or to ping a reviewer once CI is green.
---

# Review ping

The message must read as one the user typed. Never send it with
`slack_send_message` or `slack_schedule_message`: Slack stamps those with the
connector's app name. Create a draft with `slack_send_message_draft`, and press
Send in the user's own Slack web session through Claude in Chrome.

This needs Claude Code with the Slack connector, Claude in Chrome, and
background Bash that re-invokes the session. Keep the registering session and
Chrome open until CI ends; closing the session drops the ping, and the draft
stays for the user.

## Register (the user is present)

1. Read the PR with `gh pr view <pr> --json url,title,state,isDraft`. Find the
   recipient with `slack_search_users` or `slack_search_channels`.
2. Write the message in the user's voice. Search the user's own past review
   requests in Slack and match their greeting, length, and closing. Include
   the PR URL and, in a channel, a mention of the reviewer. No AI tells.
3. Create the draft. On `attached_draft_exists`, stop and ask: another draft
   or ping already holds that channel.
4. Open the channel in a new Chrome tab: the draft result's `channel_link`
   with `/archives/` replaced by `/messages/`. Wait for the composer, run the
   read script below with `javascript_tool`, and close the tab.
5. Show the user the recipient and `display`, which is how Slack shows the
   text. Check that `content` holds the PR URL and the intended mention IDs as targets.
   The user's approval covers this one send; keep `channel`, `display`, and
   `content` verbatim as the expected values. For edits, ask the user to edit the draft
   in Slack, then repeat step 4.
6. Run `gh pr checks <pr> --watch --fail-fast --interval 30` alone in a
   background Bash call and tell the user they can move on. If it ends with
   `no checks reported`, run a background `sleep 60` and watch again. After
   5 tries, stop: report that CI was not confirmed and the draft is kept.

## Send (on re-invocation)

7. Recheck in separate calls: `gh pr view <pr> --json state,isDraft,headRefOid`
   shows the PR open and not a Draft, plain `gh pr checks <pr>` exits 0, and a
   second `gh pr view` shows the same `headRefOid`. Exit 8 (pending, as after a
   new push) or a changed head means go back to step 6. Anything else means do
   not send. This guarantees that every check reported for the last head seen
   passed, not that no push lands during the click.
8. Read the newest message with `slack_read_channel` (limit 1) and note its
   timestamp. Open the channel in a new Chrome tab, wait for the composer,
   and run the send script below with the expected values as JSON strings.
9. Only an explicit `not-sent: ...` result means nothing was sent. After
   `clicked`, an error, a timeout, or no result, never run the send script
   again: read the channel with `slack_read_channel` and `oldest` set to the
   noted timestamp. The sent message is the one new message from the user
   that matches `content`. To compare, parse the message text into a list
   before decoding entities: plain text, `["mention", ID]` for `<@ID|...>`,
   and `["link", URL, label]` for `<URL|label>`, splitting at the first `|`.
   Then decode `&amp;`, `&lt;`, `&gt;` in each piece, merge adjacent text,
   and trim. Map `content` the same way: a `ts-mention` entry to
   `["mention", target]`, other entries to `["link", target, label]`. With no
   match or more than one, report the send as unknown, not failed. Close
   the tab.
10. Report the message link, or why it was not sent with the failing checks
    and their links. When not sent, the draft stays for the user to send by
    hand.

Use the tab only to open the target channel and run the scripts below. A
sign-in page means do not send. If a step before the send script fails
twice, stop and report.

## Scripts

`ser` turns the composer into a list of text pieces and
`[kind, target, label]` entries, such as `["ts-mention", "U123", "@name"]`,
`["ts-slug", "https://...", label]` for a bare URL, or `["a", "https://...",
label]` for a labeled link. `content` is that list as JSON, so a changed
label, target, or pairing of the two no longer matches.

Read:

```js
(() => {
  const ser = n => n.nodeType === 3 ? [n.data] : n.nodeType !== 1 ? [] : n.dataset.id || n.tagName === "A" ? [[n.tagName.toLowerCase(), n.dataset.url || n.dataset.id || n.getAttribute("href"), n.textContent]] : [...[...n.childNodes].flatMap(ser), ...(n.tagName === "P" ? ["\n"] : [])];
  const ed = document.querySelector('[data-qa="texty_input"]');
  return JSON.stringify({channel: location.pathname.split("/").pop(), display: ed.innerText.trim(), content: JSON.stringify(ser(ed))});
})()
```

Send:

```js
(() => {
  const channel = CHANNEL, display = DISPLAY, content = CONTENT;
  const ser = n => n.nodeType === 3 ? [n.data] : n.nodeType !== 1 ? [] : n.dataset.id || n.tagName === "A" ? [[n.tagName.toLowerCase(), n.dataset.url || n.dataset.id || n.getAttribute("href"), n.textContent]] : [...[...n.childNodes].flatMap(ser), ...(n.tagName === "P" ? ["\n"] : [])];
  if (!location.pathname.endsWith("/" + channel)) return "not-sent: wrong channel";
  const inputs = document.querySelectorAll('[data-qa="texty_input"]');
  const buttons = document.querySelectorAll('[data-qa="texty_send_button"]');
  if (inputs.length !== 1 || buttons.length !== 1) return "not-sent: composer not unique";
  let box = inputs[0];
  while (box && !box.contains(buttons[0])) box = box.parentElement;
  if (!box) return "not-sent: composer not found";
  if (box.querySelector('[data-qa^="multi-file-upload"], [data-qa^="pending_file"]')) return "not-sent: attachment";
  if (inputs[0].innerText.trim() !== display || JSON.stringify(ser(inputs[0])) !== content) return "not-sent: text changed";
  if (buttons[0].disabled) return "not-sent: send disabled";
  buttons[0].click();
  return "clicked";
})()
```
