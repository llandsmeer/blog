---
layout: post
title:  "VIM editing setup for LaTeX"
date:   2024-03-21T14:08:46.912121+00:00
categories: tech
---

# Open links for \cite{} commands

By lack of a better reference manager, here is a simple code snippet
to open the corresponding doi-link from a `\cite{}` command in latex.


```vimlang
function! OpenDoiForCite()
  let cite_name = expand('<cword>')
  let root = '.'
  let bib_files = globpath(root, '**/*.bib', 1, 1)
  for file in bib_files
    let grepre = '@[a-z]+{' . cite_name . '\s*,(\s*[a-z]+\s*=\s*{[^}]+},?\s*)+}'
    let result = system('grep -zoP "' . grepre . '" ' . file)
    if result != ''
      echo result
      let doi = matchlist(result, 'doi\s*=\s*{\([^}]\+\)}')
      if len(doi) != 0
        echo 'doi:'. string(doi[1])
        execute 'silent !chromium-browser "https://doi.org/' . doi[1] . '"<cr>'
        return
      endif
      let title = matchlist(result, 'title\s*=\s*{\([^}]\+\)}')
      if len(title) != ''
        echo 'title:'. string(title[1])
        let encoded_title = substitute(title[1], ' ', '+', 'g')
        execute 'silent !chromium-browser "https://www.google.com/search?&q=' . encoded_title . '"'
        return
      endif
    endif
  endfor
  echo "DOI or title not found for citation: " . cite_name
endfunction

autocmd FileType tex nnoremap <buffer> K :call OpenDoiForCite()<CR>
```

# Folding

```
Plug 'matze/vim-tex-fold'
```

# Outline-based navigation

```
Plug 'vim-voom/VOoM'
```

```
autocmd FileType tex nnoremap <BS> :Voom latex<cr>
autocmd FileType voomtree set nofoldenable
```

# Softwrapping

Using some neovim specific settings we obtain really nice softwraps

```
autocmd FileType tex set wrap
autocmd FileType tex set breakindent
autocmd FileType tex set breakindentopt=shift:2
autocmd FileType tex set showbreak==>
autocmd FileType tex set linebreak

nnoremap j gj
nnoremap k gk
nnoremap $ g$
nnoremap 0 g0
nnoremap ^ g^
nnoremap A g$a
nnoremap I g^i
```

# Forward Synctex

I'm using Evince to view PDFs (the ubuntu default)

```
wget 'https://raw.githubusercontent.com/Vinno97/evince-synctex/master/evince-synctex.sh'
```

Then in neovim:

```
autocmd CursorMoved <buffer> :execute "!bash evince-synctex.sh sync ./build/main.pdf main.tex " . line(".")
```


