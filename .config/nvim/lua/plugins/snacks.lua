-- Enable snacks.image: inline images via kitty graphics (verified inside herdr panes).
-- Non-PNG formats additionally need imagemagick (Brewfile).
-- Picker list keys follow the VSCode muscle memory: cmd+j/k = next/prev, cmd+l = confirm.
return {
  {
    "folke/snacks.nvim",
    opts = {
      image = { enabled = true },
      picker = {
        win = {
          input = {
            keys = {
              ["<D-j>"] = { "list_down", mode = { "i", "n" } },
              ["<D-k>"] = { "list_up", mode = { "i", "n" } },
              ["<D-l>"] = { "confirm", mode = { "i", "n" } },
            },
          },
        },
      },
    },
  },
}
