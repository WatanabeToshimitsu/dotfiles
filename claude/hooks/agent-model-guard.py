#!/usr/bin/env python3
"""Deny Agent calls that leave the subagent's model to inheritance or a default."""

import json
import sys

REASON = ("Agent 呼び出しには model（sonnet、opus、haiku、fable のいずれか）を明示してください。"
          "作業の難しさに合うものを選び、親のモデルを引き継がせないでください。")


def main():
    data = json.load(sys.stdin)
    tool_input = data.get("tool_input") or {}
    # Why not deny forks: a fork always runs on its parent's model and rejects a model parameter.
    if data.get("tool_name") != "Agent" or tool_input.get("subagent_type") == "fork" or tool_input.get("model"):
        return
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": REASON}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
