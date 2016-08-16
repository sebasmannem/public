set nocompatible
filetype plugin indent on
set lazyredraw
set titleold=
set nofoldenable
set shell=bash
set showmode
set visualbell
set background=dark
set ttyfast
set linebreak
set incsearch
set expandtab
set smartcase
set ignorecase
set backspace=indent,eol,start
set showcmd
set showmatch
set autoindent
set fileformats=unix,dos
set preserveindent
set wrap
set scrolloff=5
set sidescrolloff=5
set sw=4
set ts=4
set sts=4
set smarttab

au BufRead,BufNewFile *.yml,*.yaml,*.eyaml set ft=yaml
autocmd FileType yaml setlocal shiftwidth=2 tabstop=2
syntax on

