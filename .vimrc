set fenc=utf-8
set nobackup
set noswapfile
set autoread
set hidden
set showcmd


set number
set virtualedit=onemore
set smartindent
set visualbell
set showmatch
" ステータスラインを常に表示
set laststatus=2
set wildmode=list:longest
" 折り返し時に表示行単位での移動できるようにする
nnoremap j gj
nnoremap k gk
syntax enable


set expandtab
set tabstop=2
set shiftwidth=2


set ignorecase
" 検索文字列に大文字が含まれている場合は区別して検索する
set smartcase
set incsearch
set wrapscan
set hlsearch
nmap <Esc><Esc> :nohlsearch<CR><Esc>


" vim-herdr-navigation: seamless Ctrl+h/j/k/l across vim splits and herdr panes
" (plugin is installed/updated by `herdr plugin`, hence the versioned glob)
if !empty($HERDR_PANE_ID)
  for s:herdr_nav in glob('~/.config/herdr/plugins/github/vim-herdr-navigation-*/editor/vim.vim', 0, 1)
    execute 'source' fnameescape(s:herdr_nav)
    break
  endfor
endif
