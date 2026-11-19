---
name: review-ping
description: Register a Slack review request for a pull request once, then send it from the user's own Slack session only after CI passes, so the user can move on right away. Use when the user asks to send, queue, or schedule a Slack review request, or to ping a reviewer once CI is green.
---

# Review ping

Never send with `slack_send_message` or `slack_schedule_message`: Slack stamps
those with the app name. Draft with `slack_send_message_draft`, then press Send
in the user's Slack web session through Claude in Chrome. Keep this session
and Chrome open until CI ends; if either closes, the draft stays unsent.

## Register

1. Destination: a DM only if the user asks for one; otherwise a named person
   is the reviewer to mention in a channel. Fill an unnamed channel or
   reviewer from the user's recent review requests for the same repository
   (`from:<@USER_ID> github.com/<owner>/<repo>/pull`) when they agree.
   Otherwise ask, listing a few names to copy: channels the user often sends
   review requests to, channels named after the repository or project, past
   reviewers. Before using a channel the user did not name, read its topic;
   if it sends review requests elsewhere, tell the user.
2. Write the message like the user's past review requests: same greeting,
   length, and closing, with the mention and the PR URL.
3. Create the draft; on `attached_draft_exists`, stop and ask. Open the
   result's `channel_link`, with `/archives/` replaced by `/messages/`, in a
   new Chrome tab, run the script below with `EXPECTED = null`, and close
   the tab.
4. Show the destination as `#channel` or `DM to <name>`, and `display`.
   Approval covers this one send; keep `channel` and `content` verbatim. For
   edits, the user edits the draft in Slack and you repeat step 3.
5. Run `gh pr checks <pr> --watch --fail-fast --interval 30` alone in a
   background Bash call, and tell the user they can move on. On `no checks
   reported`, run a background `sleep 60` and watch again; after 5 tries,
   report CI as unconfirmed.

## Send

6. In separate calls, `gh pr view <pr> --json state,isDraft,headRefOid` must
   show an open, non-Draft PR, `gh pr checks <pr>` must exit 0, and a second
   `gh pr view` must show the same head. Exit 8 means go back to step 5;
   anything else means do not send.
7. Note the newest message timestamp with `slack_read_channel`. Open the
   channel in a new tab and run the script with the kept values.
8. Only `not-sent: ...` means nothing was sent. After any other result or
   none, never run the script again. Read the messages after the noted
   timestamp: exactly one new message from the user holding the PR URL is
   the sent one; otherwise report the result as unknown. Close the tab and
   report the message link, or why it was not sent and the draft is waiting.

## Script

With `EXPECTED = null` it returns the composer as `{channel, display,
content}`; `content` lists text and `[kind, target, label]` for each mention
and link. With the kept values it waits until 20 seconds after page load
(Slack ignored an earlier click), checks the channel, composer, attachments,
and content, clicks Send once, and waits for the composer to clear.

```js
await (async () => {
  const EXPECTED = null; // or {channel: "...", content: "..."}
  const ser = n => n.nodeType === 3 ? [n.data] : n.nodeType !== 1 ? [] : n.dataset.id || n.tagName === "A" ? [[n.tagName.toLowerCase(), n.dataset.url || n.dataset.id || n.getAttribute("href"), n.textContent]] : [...[...n.childNodes].flatMap(ser), ...(n.tagName === "P" ? ["\n"] : [])];
  if (EXPECTED) await new Promise(r => setTimeout(r, Math.max(0, 20000 - performance.now())));
  const eds = document.querySelectorAll('[data-qa="texty_input"]');
  const btns = document.querySelectorAll('[data-qa="texty_send_button"]');
  if (eds.length !== 1 || btns.length !== 1) return "not-sent: composer not unique";
  const [ed, btn] = [eds[0], btns[0]];
  const now = {channel: location.pathname.split("/").pop(), display: ed.innerText.trim(), content: JSON.stringify(ser(ed))};
  if (!EXPECTED) return JSON.stringify(now);
  let box = ed;
  while (!box.contains(btn)) box = box.parentElement;
  if (box.querySelector('[data-qa^="multi-file-upload"], [data-qa^="pending_file"]')) return "not-sent: attachment";
  if (now.channel !== EXPECTED.channel || now.content !== EXPECTED.content || btn.disabled) return "not-sent: changed";
  btn.click();
  for (let i = 0; i < 20; i++) {
    await new Promise(r => setTimeout(r, 500));
    if (!ed.isConnected || !ed.innerText.trim()) return "clicked";
  }
  return "unknown: composer not cleared";
})()
```
