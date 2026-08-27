-- markdown-preview.nvim: the extra's default build (mkdp#util#install) is async
-- and can no-op during headless bootstraps, leaving app/node_modules missing
-- ("Cannot find module 'tslib'"). Build synchronously with npm instead.
--
-- The extra only lazy-loads the plugin on <leader>cp / :MarkdownPreview. Load it
-- on the filetype instead so g:mkdp_auto_start opens the live browser preview as
-- soon as a markdown buffer is entered (FileType fires before BufEnter, so the
-- auto_start autocmd is registered in time for the buffer that triggered it).
return {
  {
    "iamcco/markdown-preview.nvim",
    build = "cd app && npm install --no-fund --no-audit",
    ft = { "markdown", "markdown.mdx" },
    init = function()
      vim.g.mkdp_auto_start = 1
      vim.g.mkdp_auto_close = 1
      vim.g.mkdp_theme = "dark"
      vim.g.mkdp_echo_preview_url = 1

      -- Open the preview without pulling focus away from the editor. Drop the
      -- -g flag to have the browser come to the front instead.
      if vim.fn.has("mac") == 1 then
        vim.cmd([[
          function! MkdpOpenInBackground(url) abort
            call system('open -g ' . shellescape(a:url))
          endfunction
        ]])
        vim.g.mkdp_browserfunc = "MkdpOpenInBackground"
      end
    end,
  },
}
