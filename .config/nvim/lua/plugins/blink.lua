-- VSCode-style completion menu keys: cmd+j/k = next/prev, cmd+l = accept
return {
  {
    "saghen/blink.cmp",
    opts = {
      keymap = {
        ["<D-j>"] = { "select_next", "fallback" },
        ["<D-k>"] = { "select_prev", "fallback" },
        ["<D-l>"] = { "select_and_accept", "fallback" },
      },
    },
  },
}
