---
layout: post
title:  "Automatically send all Matplotlib plots to your phone via telegram-send"
date:   2021-04-06 00:36:00 +0200
categories: tech
comments: true
---

So I'm not actually sure if this is actually a good idea, but at least its a fun one :).
For my research I usually run long (>20mins) simulations using quickly written scripts
and it would be nice if those scripts automagically notified me when they where ready.
Of course there are clean solutions to this problem, but they would probaly involve adding
extra code to the scripts (which I would have to remember doing everytime!) or black box methods
that would just send a message when a long running python process is done (boring!).

Instead, everytime when a python script displays its final result using a `matplotlib.show()` call,
it will also send that plot to my phone via telegram. Simple :). As I couldn't find a elegant way to
implement this, I extended the Qt5Agg backend a bit with custom code. Here's how to do this:

Install telegram-send:

```sh
pip3 install telegram-send
telegram-send --configure
```

Create a custom backend that derives from Qt5Agg.

```python
# backend_mpl_telegram_send.py
import sys
import datetime
import subprocess
from matplotlib.backend_bases import Gcf
import matplotlib.backends.backend_qt5agg as qt5agg

PATH = '/tmp/mpl_telegram_send.png'

class FigureManagerMPLTelegramSend(qt5agg.FigureManager):
    def show(self):
        self.canvas.figure.savefig(PATH)
        try:
            fn = sys.modules['__main__'].__file__
        except:
            fn = '<interactive>'
        date = datetime.datetime.now().isoformat()
        subprocess.Popen([
            'telegram-send',
            '--image', PATH,
            '--caption', f'{fn} {date}'])
        super().show()

@qt5agg._BackendQT5Agg.export
class _BackendMPLTelegramSend(qt5agg._BackendQT5Agg):
    FigureManager = FigureManagerMPLTelegramSend
```

Presumable you'd be able to use the actual python API of telegram-send, but
this works as well and runs concurrently in the background.

Now put these two lines in you bashrc:

```sh
export PYTHONPATH=/path/to/directory/with/you/python/file
export MPLBACKEND="module://backend_mpl_telegram_send"
```

And test it :)

```python
import numpy as np
import matplotlib.pyplot as plt

x = np.linspace(0, 10)
plt.plot(x, np.sin(x))
plt.show()
```
