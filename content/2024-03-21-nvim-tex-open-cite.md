---
layout: post
title:  "Open cite-reference from bibtex in when editing latex in vim"
date:   2024-03-21T14:08:46.912121+00:00
categories: tech
---

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
