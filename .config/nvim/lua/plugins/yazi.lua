-- yazi.nvim: open the yazi file manager from within nvim (browse-hub integration).
-- <leader>e (snacks explorer) stays the default in-editor tree.
return {
  {
    "mikavilpas/yazi.nvim",
    dependencies = { "folke/snacks.nvim" },
    keys = {
      { "<leader>fy", mode = { "n", "v" }, "<cmd>Yazi<cr>", desc = "Yazi (current file)" },
      { "<leader>fY", "<cmd>Yazi cwd<cr>", desc = "Yazi (cwd)" },
    },
    opts = {},
  },
}
