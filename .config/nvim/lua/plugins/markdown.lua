-- markdown-preview.nvim: the extra's default build (mkdp#util#install) is async
-- and can no-op during headless bootstraps, leaving app/node_modules missing
-- ("Cannot find module 'tslib'"). Build synchronously with npm instead.
return {
  {
    "iamcco/markdown-preview.nvim",
    build = "cd app && npm install --no-fund --no-audit",
  },
}
