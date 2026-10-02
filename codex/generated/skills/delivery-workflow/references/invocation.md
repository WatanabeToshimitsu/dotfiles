# Invocation routes

## CLI requirements

Use private packet/evidence directories and explicit stdin. Verify installed
CLI support and retain normal rules, sandbox, configuration, and authentication.
These examples specify invocations; they are not run evidence. Replace
placeholders and read only the applicable example below.

Apply the stage contract's fallback if a model is rejected; never bypass a
permission denial. Record actual requested/observed model and evidence source.
Missing identity stays unknown, not frontier approval. Reviewers use only the
packet; implementation needs the handed-off paths and writer authority.

## Codex review

Codex's read-only sandbox prevents writes, not unrelated reads. Explicitly
instruct the fresh B or D reviewer to use only the packet and invoke no tools.
Native explicit model dispatch or actual client metadata establishes model
evidence; the CLI model argument is only a request.

```bash
rtk proxy codex exec -m gpt-6-astra -C "<packet-dir>" --skip-git-repo-check \
  --ephemeral --sandbox read-only --json \
  --output-last-message "<evidence>/design-review.md" - \
  < "<packet-dir>/packet.md" > "<evidence>/design-review.jsonl"
```

## Codex implementation

C receives exact allowed paths, base/ref, and exclusive writer authority.
Retain normal configuration and permissions. C hands back checks and artifacts
without committing or pushing; the lead handles authorized delivery after D.

```bash
rtk proxy codex exec -m gpt-6-astra -C "<worktree>" --sandbox workspace-write \
  --json --output-last-message "<evidence>/implementation.md" - \
  < "<packet-dir>/packet.md" > "<evidence>/implementation.jsonl"
```

## Claude review

Native `fable-deep` retains read-only tools: a packet-only prompt does not isolate
unrelated files. Prefer the tool-less CLI below when tool isolation is needed.
Supply only the packet to the fresh B or D reviewer. Extract actual model
evidence from `modelUsage` when present; absent fields remain unknown.

```bash
rtk proxy claude --restricted --tools '' --disallowedTools 'mcp__*' \
  --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
  --disable-slash-commands --no-chrome \
  --no-session-persistence --model fable --effort high --print --output-format json \
  < "<packet-dir>/packet.md" > "<evidence>/implementation-review.json"
```
