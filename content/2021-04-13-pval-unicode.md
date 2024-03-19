---
layout: post
title:  "Printing p-values using unicode superscripts in R"
date:   2021-04-13 00:00:00 +0100
categories: tech
---

This is a pretty simple one. I wanted to show some nicely formatted p-values on a plot by an external library, but it wasn’t possible to pass anything else than a character vector as labels. So I built this function that formats any p-value using unicode characters. Hopefully it’s of use to others as well:

```R
pval = function (ps) {
    superscript = c('\u{2070}', '\u{00b9}', '\u{00b2}', '\u{00b3}', '\u{2074}',
                    '\u{2075}', '\u{2076}', '\u{2077}', '\u{2078}', '\u{2079}')
    sapply(ps, function(p) {
        if (is.na(p)) return("")
        if (p < 0 || p > 1) return (sprintf("%.2f", p))
        e = ceiling(-log10(abs(p)))
        s = paste0(lapply(utf8ToInt(toString(e)), function(d) { superscript[d - 48 + 1] }), collapse='')
        sprintf('%.1f%s10%s%s', p / 10^-e, '\u{2715}', '\u{207b}', s)
    })
}
```

For example:

```
# pval(c(0.1, 0.01, 0.001))
[1] "1.0✕10⁻¹" "1.0✕10⁻²" "1.0✕10⁻³"

# pval(0.1)
[1] "1.0✕10⁻¹"
```
