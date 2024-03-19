---
layout: post
title:  "Fast searching in a sorted genetics file & the curse of gzip compression"
date:   2019-12-28 21:07:00 +0100
categories: tech
comments: true
---

As a bioinformatician,
how often have you found yourself staring at the screen waiting for `grep`
to find a certain gene or chromosome-basepair location in a gargantuan vcf, bed or gwas file?
And then realize you forgot adding a field delimiter to your pattern so your search
included way too much results?
Thats a problem I have wanted so solve for a long time.

Luckily, these files are usually sorted, which means we should be able to use a binary search!
So thats what I wrote this weekend;
a tool you can use to instantly find genomic regions
in anything from vcfs, bed files, csv data, gwas to plink genetic statistics with
a friendly user interface.
As implementing a binary sort on a text file
presented me with a lot of interesting challenges, skip below for some implementation details.

```
$ time grep -E '11 119[0-9]{3} ' data
--- 11:119854:T:G 11 119854 T G G T 623.98 0.02301 0 624 0 0 1.8438e-05 -0 0 0 0.011331 1.84374e-05
--- 11:119945:G:C 11 119945 G C C G 622.6 1.3961 0 623 1 0 0.0011187 -0 0 0 0.71666 0.00111868
10,98s (9,84s(u) + 1,14s(s) 4kb 33+1 ctx)

$ time python3 gensearch.py -f data --chr Chr --bp BP chr11:119500/1000
SNPID RSID Chr BP A_allele B_allele MinorAllele MajorAllele AA AB BB AA_calls AB_calls BB_calls MAF HWE missing missing_calls Info CAF
--- 11:119854:T:G 11 119854 T G G T 623.98 0.02301 0 624 0 0 1.8438e-05 -0 0 0 0.011331 1.84374e-05
--- 11:119945:G:C 11 119945 G C C G 622.6 1.3961 0 623 1 0 0.0011187 -0 0 0 0.71666 0.00111868
0,11s (0,08s(u) + 0,03s(s) 14kb 0+1 ctx)
```

<!--

```
$ python3 gensearch.py -f stats
Missing --chr or --bp. Possible column names are:
SNPID         (rs22806.., rs36046.., rs14091.., rs68941.., ..)
Chr           (15, 13, 20, 0X, ..)
BP            (5088456, 45730252, 32947066, 89827248, ..)
A_allele      (CAG, AAG, TTA, GTTGT, ..)
B_allele      (CATA, CAG, TTA, GTCCC, ..)
MinorAllele   (CATA, CAG, AAG, TTA, ..)
MajorAllele   (CAG, TTA, GTTGT, TC, ..)
[...]

$ python3 gensearch.py -f stats --chr Chr --bp BP
No query specified
Available regions:
01:10177-249240543
02:10179-243188367
03:60069-197962381
04:10005-191043881
05:10043-180904689
[...]
```
-->

# Implementation

Here are some interesting challenges and their solutions
for searching in sorted files. These are all genetic data agnostic,
so maybe they'll be of use in other projects as well.

#### Reading between the lines

As we perform our binary search, we'll jump from one
file position to another, until we find the line matching the user's query.
These positions are most likely not at the
start of a line. So we need some kind op method to read
one or more lines given a position in the file.
Why more than one line? Continue reading :)

```python
def read_lines_at(f, pos, nlines=1, buffer_size=40960):
    '''reads <nlines> complete lines from binary stream f at pos.

    read_lines_at() searches for the first occurance of
    a newline, then proceeds from there by returning the
    next <nlines> complete lines. When (the nonnegative) <pos> is zero,
    the initial search is skipped.
    All lines must be contained in a read of <buffer_size> from pos.
    If this does not fit, the function fails.
    If EOF is found as the last line, b'' is returned instead (like
    f.read() at EOF). Another read after that would result in failure.

    read_lines_at() returns a tuple (position of line start, [lines]).
    On failure, (_, None) is returned.
    '''
    f.seek(pos)
    lines = []
    data = f.read(buffer_size)
    if data:
        s = data.find(b'\n')+1 if pos > 0 else 0
        if s == 0 and pos != 0 and len(data) == buffer_size:
            # buffer size is not large enough
            return -1, None
        line_start = pos + s
        e = s
        for idx in range(nlines):
            e = data.find(b'\n', s)
            if e == -1:
                if idx < nlines - 1:
                    return line_start, None
                e = None
            lines.append(data[s:e])
            if e is not None:
                s = e + 1
        return line_start, lines
    else:
        return pos, None
```

#### Binary search in a text file

Next up, our binary search itself!
Remember, normally we start in the middle of a sorted array.
There, we compare our query item with that element, and
then either perform the algorithm on the region below or above the middle,
or our element is the right element and we return its index.
However, region queries usually turn up much more than one index.
So we need to find the *leftmost* match for our query, and then just read
lines until the query does not match anymore.

To make a binary search find this leftmost line, we need to look at two lines
at the same time. Then the 'element' our algorithm is looking for, are the two
consecutive lines where the first line does not match the query, and the second line
does. This combined with some logic for the first and last lines, I ended up with:

```python
def search_left(f, seek_from, seek_to, value, keyf):
    '''finds the first line for which keyf(at, line) == value.'''
    a, b = seek_from, seek_to
    while a != b:
        pos = (a + b) // 2
        line_start, (left, right) = read_lines_at(f, pos, nlines=2)
        left_value = keyf(line_start, left) if left else None
        right_value = keyf(line_start, right) if right else None
        if left_value != value and right_value == value:
            return line_start + len(left) + 1, right
        elif not right or right_value >= value:
            b = pos
        elif right_value < value:
            if a + 1 == b:
                break
            a = pos
    if pos == 0:
        line_start, (first_line,) = read_lines_at(f, 0, 1)
        if keyf(line_start, first_line) == value:
            return 0, first_line
        return 0, None
    return seek_to - 1, None
```

#### Unrolled breadth first search

While the lines within for a certain chromosome are
usually sorted with respect to basepair position,
the chromosomes themselves are not always sorted in a file.
So you have to poke the file in a smart way until you find
one occurancy of your query chromosome.
Let's call this the pivot line.
Then you can define a complete order on the file by
comparing a chromosome's name with the query chromsome.
If they are not equal, compare the line's position with the position of the pivot line.

So what is a simple and reasonable smart way of poking our file?
A breadth first search! Thinking of how to implement that on
an array was a fun excercise, but ended up being quite simple.
Performing it on a 'array' with indices continuous in the range 0-1,
the traversal would follow: 1/2; 1/4, 3/4; 1/8, 3/8, 5/8, 7/8 etc..
Then the pattern is fairly obvious.

```python
def bfs_indices(length, depth=None):
    '''generates linear breadth first search indices.

    Returns array indices as if a breadth first search
    is performed on a binary tree constructed from a
    sorted linear array of length <length>. Defaults
    to a search through the entire array, but early
    stopping is possible by providing the maximum
    tree search level <depth>.

    >>> list(linear_bfs_indices(length=10))
    [5, 2, 7, 1, 3, 6, 8, 0, 1, 3, 4, 5, 6, 8, 9]
    >>> list(linear_bfs_indices(length=512, depth=3))
    [256, 128, 384, 64, 192, 320, 448]
    >>> len(set(linear_bfs_indices(length=10)))
    10
    '''
    denom = 2
    if depth is None:
        depth = length.bit_length()
    while depth != 0:
        for num in range(1, denom, 2):
            yield length * num // denom
        depth, denom = depth-1, denom*2
```

#### The curse of gzip compression

Still then, there is the annoying problem that
all these neatly sorted files are usually compressed with `gzip` -
which does not allow random access halfway the file in the general case.
Thus searching can only be done by reading the file line by line,
even though there are compression tools available like `bgzip`
(or maybe `dictzip` or `bzip2`, see [stackoverflow])
that create a compressed file for which binary search would work perfectly,
readable on all systems by default, with only slightly larger file sizes...
`bgzip` is usually used for vcf and bed files together with `tabix`,
but by itself it already provides enough information for fast searching.

[stackoverflow]: https://stackoverflow.com/questions/429987/compression-formats-with-good-support-for-random-access-within-archives

I did some expriments that showed that with a lot of hard work
random access to a `gzip` seems to be possible for
files compressed with the default flags.
Maybe there will be a post on that later.

**Later**: so I modified [a public deflate implementation](https://github.com/jibsen/tinf)
s.t. it would be able to start halfway a gzip file and continue reading from there,
keeping track of known and unknown output characters. More general, it doesn't only
read gzip files, but any random container format containing DEFLATE compressed data.
Under the constraint of only outputting printable ascii characters, we can recover
data after starting randomly inside a DEFLATE stream. Sadly, this only works for files
with very low complexity (like `seq 1 100000`), not for genetics files because `gzip` likes
to create arbitrary long (~100 MB's) backreferences in its output for neglible compression
gains. Anyway, if you need a program that's able to recover DEFLATE streams from unknown
container files, it's [available here](https://github.com/llandsmeer/gzip-random-seek).
