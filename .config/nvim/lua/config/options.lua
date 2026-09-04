-- Options are automatically loaded before lazy.nvim startup
-- Default options that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/options.lua
-- Add any additional options here

-- K must be mapped BEFORE any LSP attaches: the nvim runtime installs its
-- buffer-local K=hover default only when K is unmapped at LspAttach time,
-- and config/keymaps.lua loads too late (VeryLazy) for the first buffer.
-- Hover lives on gh instead (see config/keymaps.lua).
vim.keymap.set({ "n", "x" }, "K", "10k", { desc = "Up 10 lines" })
