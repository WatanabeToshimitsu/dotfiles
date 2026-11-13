---
paths:
  - "**/*.{c,cc,cpp,cs,go,java,js,jsx,kt,kts,php,py,pyi,rb,rs,swift,ts,tsx,vue,svelte}"
  - "**/*.{json,yaml,yml,toml}"
---
# Security

## Secrets

- Validate required secrets before use; when missing or empty, fail without
  disclosing their values.

## When something is found

1. Stop the unsafe action and establish severity and scope before changing anything.
2. Fix critical issues before returning to the original task.
3. Rotate anything exposed.
4. Check the rest of the same boundary for the identical pattern. Do not expand
   into unrelated cleanup.
