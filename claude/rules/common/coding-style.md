---
paths:
  - "**/*.{c,cc,cpp,cs,go,java,js,jsx,kt,kts,php,py,pyi,rb,rs,swift,ts,tsx,vue,svelte}"
---
# Coding Style

Match the file being edited. Its naming convention, error handling, and structure
outrank anything here. `golang/`, `python/`, and `typescript/` are more specific
than this file and win where they disagree with it.

- Return early instead of stacking conditionals.
- Name the constant instead of inlining a threshold, delay, timeout, or limit.
- Handle or report every error; never swallow one silently.
- Validate data crossing a system boundary before acting on it.
