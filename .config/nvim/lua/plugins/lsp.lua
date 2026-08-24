-- Drop LazyVim's buffer-local LSP keymaps that clash with the vscodevim port:
-- K is 10k (travel); hover lives on gh (see config/keymaps.lua).
return {
  {
    "neovim/nvim-lspconfig",
    opts = {
      servers = {
        ["*"] = {
          keys = {
            { "K", false },
          },
        },
      },
    },
  },
}
