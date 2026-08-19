-- Enable snacks.image: inline images via kitty graphics (verified inside herdr panes).
-- Non-PNG formats additionally need imagemagick (Brewfile).
return {
  {
    "folke/snacks.nvim",
    opts = {
      image = { enabled = true },
    },
  },
}
