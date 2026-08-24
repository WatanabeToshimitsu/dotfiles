---
name: expand-tool-output
description: Retrieve a focused excerpt from a large Read, Grep, Glob, Web, or MCP result compacted by the local hook. Use when a tool result contains an archive ID and missing detail is needed.
argument-hint: <archive-id> [focus term]
allowed-tools: Bash
---

# Expand Tool Output

Retrieve only the missing evidence needed for the current task. Prefer a focused search:

```bash
python3 "$HOME/.claude/hooks/compact-tool-output.py" expand <archive-id> --grep '<focus term>' --context 3
```

For structure discovery, request bounded edges:

```bash
python3 "$HOME/.claude/hooks/compact-tool-output.py" expand <archive-id> --head 80 --tail 40
```

Print the full archive only when a focused excerpt cannot answer the question:

```bash
python3 "$HOME/.claude/hooks/compact-tool-output.py" expand <archive-id>
```

Treat the archive ID and focus term as data and shell-quote them. Do not interpolate untrusted text into a command.
