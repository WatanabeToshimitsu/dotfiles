-- Keymaps are automatically loaded on the VeryLazy event
-- Default keymaps that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here

-- Ported from the vscodevim setup (vscode/settings.json "vim.*" keys).
-- LazyVim defaults intentionally overridden: H/L (buffer switch -> use [b / ]b),
-- K (LSP hover -> use gh), <leader>l (Lazy UI -> use :Lazy),
-- <leader>/ (grep -> use <leader>sg), <leader>: (cmd history -> use q:).

local map = vim.keymap.set

-- jk leaves insert mode
map("i", "jk", "<Esc>", { desc = "Exit insert mode" })

-- Faster travel
map({ "n", "x" }, "J", "10j", { desc = "Down 10 lines" })
map({ "n", "x" }, "K", "10k", { desc = "Up 10 lines" })
map({ "n", "x" }, "H", "b", { desc = "Previous word" })
map({ "n", "x" }, "L", "w", { desc = "Next word" })
map("n", "gh", vim.lsp.buf.hover, { desc = "Hover (K is remapped)" })

-- snake_case hops
map({ "n", "x" }, "\\", "f_", { desc = "Next underscore" })
map({ "n", "x" }, "_", "F_", { desc = "Previous underscore" })

-- Line start/end, also while an operator is pending
map({ "n", "x", "o" }, "<leader>h", "^", { desc = "Line start" })
map({ "n", "x", "o" }, "<leader>l", "$", { desc = "Line end" })

-- Join lines (J is remapped above)
map("n", "<leader>j", "J", { desc = "Join lines" })

-- Blank line without entering insert mode
map("n", "<leader>o", "o<Esc>", { desc = "Blank line below" })
map("n", "<leader>O", "O<Esc>", { desc = "Blank line above" })

-- Keep search jumps centered
map("n", "n", "nzz")
map("n", "N", "Nzz")
map("n", "*", "*zz")
map("n", "#", "#zz")

-- Visual star: search for the current selection
map("x", "*", [[y/\V<C-r>=escape(@", '/\')<CR><CR>]], { desc = "Search selection" })

-- Clear search highlight
map({ "n", "x" }, "<leader><Esc>", "<cmd>nohlsearch<cr>", { desc = "Clear hlsearch" })

-- Command palette / document symbols (VSCode: <leader>: / <leader>/)
map("n", "<leader>:", function() Snacks.picker.commands() end, { desc = "Commands" })
map("n", "<leader>/", function() Snacks.picker.lsp_symbols() end, { desc = "Document symbols" })
