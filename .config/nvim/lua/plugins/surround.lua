-- vscodevim-compatible surround keys (ys/ds/cs) instead of the extra's gsa/gsd/gsr
return {
  {
    "nvim-mini/mini.surround",
    opts = {
      mappings = {
        add = "ys",
        delete = "ds",
        replace = "cs",
        find = "",
        find_left = "",
        highlight = "",
        update_n_lines = "",
      },
    },
  },
}
