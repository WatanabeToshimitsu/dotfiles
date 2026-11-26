# Invocation routes

## CLI requirements

Use private packet/evidence directories and explicit stdin. Verify installed
CLI support and retain normal rules, sandbox, configuration, and authentication.
These examples specify invocations; they are not run evidence. Replace
placeholders and read only the applicable example below.

Apply the stage contract's fallback if a model is rejected; never bypass a
permission denial. Implementation needs the handed-off paths and writer
authority.

## Review copy

Give each B or D reviewer its own disposable worktree at the reviewed head, and
remove it after the review.

```bash
git worktree add --detach "<copy>" "<reviewed-head>"
git worktree remove --force "<copy>"
```

## Codex review

```bash
rtk proxy codex exec -m gpt-6-astra -C "<copy>" --sandbox workspace-write \
  --json --output-last-message "<evidence>/review.md" - \
  < "<packet-dir>/request.md" > "<evidence>/review.jsonl"
```

## Codex implementation

C receives exact allowed paths, base/ref, and exclusive writer authority.
Retain normal configuration and permissions. C hands back checks and artifacts
without committing or pushing; the lead handles authorized delivery.

```bash
rtk proxy codex exec -m gpt-6-astra -C "<worktree>" --sandbox workspace-write \
  --json --output-last-message "<evidence>/implementation.md" - \
  < "<packet-dir>/packet.md" > "<evidence>/implementation.jsonl"
```

## Claude review

Run native `fable-deep` with the copy's path in the request.
