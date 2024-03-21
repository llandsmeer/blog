#!/usr/bin/env python3

import os, sys

from datetime import datetime, timezone

current_iso_date = datetime.now(timezone.utc).isoformat()
current_yyyy_mm_dd = datetime.now().strftime('%Y-%m-%d')

slug = '-'.join(sys.argv[1:])
if not slug:
    slug = input('filename: ')
slug = slug.replace(' ', '-')

fn = f'content/{current_yyyy_mm_dd}-{slug}.md'

if os.path.exists(fn):
    print('file exists', fn)
    exit(1)

title = slug.replace('-', ' ').title()

content = f'''---
layout: post
title:  "{title}"
date:   {current_iso_date}
categories: tech
status: draft
---

'''

print(fn)
with open(fn, 'w') as f:
    print(content, file=f)

os.execl('/home/llandsmeer/.local/bin/nvim', 'nvim', fn)

