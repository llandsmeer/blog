---
layout: post
title:  "Online presenting in front of your slides with a transparent GTK window and OpenCV"
date:   2021-04-07 17:00:00 +0100
categories: tech
comments: true
---

Today I had to give a presentation on my research for a course to improve my presenting skills.
I thought it would be nice to recreate an in-person presenting environment, instead of my regular
share-slides-and-hear-my-voice-but-don't-see-my-face online presentation. A bit like how
Daniel Shiffman presents [The Coding Train](https://www.youtube.com/channel/UCvjgXvBlbQiydffZU7m1_aw) :).

In zoom, this is a builtin option. Share desktop as your webcam virtual background.
Nice, except they decided not to implement this on linux for some reason (WHY?!).
So I decided to build this myself.

**TLDR**: If you just want the code: [click here](#full-code)

There are roughly two ways to go about this.
Initially I tried writing a program that takes frames from the desktop and webcam,
combines them and then presents itself as a new webcam available in your favorite streaming program.
For this I used [vidgear.gears.ScreenGear](https://abhitronix.github.io/vidgear/latest/bonus/reference/screengear/),
which ended up introducing a >10 second delay.
This is probably fixable, but I deciced to pursue a different route.

Instead, I wrote a program that displays your webcam directly on your desktop.
Yes, there are a lot of programs that do that, but this one is transparent where it detects a white wall.
So after starting the program you just turn on screen sharing and give your presentation :)

Figuring out *how* to do this was a bit harder. Most graphical interface python libraries out there
do not support transparent windows. The only options seemed to be GTK and OpenGL.
PyQT5 supposedly supports it but I couldn't figure out how. Python GTK documentation is a bit hard to
read, but after a while I figured it out:

Luckily [Kurt Jacobson](https://gist.github.com/KurtJacobson/374c8cb83aee4851d39981b9c7e2c22c)
provided a gist (MIT licensed) that shows how to make a transparent window.
Next we need to draw our webcam image. Here's the procedure:

## How to draw a numpy array in GTK/Cairo

Set up OpenCV to capture your webcam and obtain a frame.

```python
cap = cv2.VideoCapture(cameraid)
ret, frame = cap.read()
```

Apparantly there are three different ways of drawing images to a GTK window,
the cairo method being the fastest. To convert your numpy array to a cairo surface:

```python
frame = cv2.cvtColor(frame[:,:,::-1], cv2.COLOR_BGR2RGBA)
# {.. insert code to modify alpha channel here..}
surface = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, W, H)
```

`ImageSurface.create_for_data` allocates memory and copies the numpy array into that memory.
That's an expensive operation you do not want to do every frame. So every frame after that
(of the same size), you should just copy over:

```python
buf = np.frombuffer(surface.get_data(), dtype='uint8')
np.copyto(buf, data.flatten())
```

And then its a simple
```python
context.set_source_surface(self.surface, 0, 0)
context.paint()
```

## Full code

Here is the script. Run it as any other python program (after installing the dependencies).
Point your webcam at a white surface and go stand in front of it.
You can use `j`/`k` to change the transparancy gradient steepness and `h`/`l` to change the threshold value.
Change the `cameraid` value to switch webcams.
Good luck presenting :)

```python
import numpy as np

import cairo
import gi
import cv2

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')

from gi.repository import Gtk
from gi.repository import Gdk, GdkPixbuf

class TransparentWindow(Gtk.Window):
    def __init__(self, cameraid=0):
        Gtk.Window.__init__(self)


        self.connect('destroy', Gtk.main_quit)
        self.connect('draw', self.draw)

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited(): self.set_visual(visual)

        self.set_app_paintable(True)
        self.show_all()
        self.surface = None
        self.a = 2
        self.b = 0
        self.connect("key_press_event", self.handle_keypress)
        self.mask = 0

        self.cap = cv2.VideoCapture(cameraid)
        ret, frame = self.cap.read()
        self.H, self.W, _C = frame.shape
        self.set_size_request(self.W, self.H)
        self.set_title('')

    def handle_keypress(self, widget, event):
        if event.keyval == ord('k'): self.a += 0.5
        if event.keyval == ord('j'): self.a -= 0.5
        if event.keyval == ord('l'): self.b += 1
        if event.keyval == ord('h'): self.b -= 1
        if event.keyval == ord('r'): self.a, self.b = 2, 0
        if self.a <= 0 : self.a = 0.01

    def draw(self, widget, context):
        W, H = self.W, self.H
        w, h = self.get_size()
        ret, frame = self.cap.read()
        frame = frame[:, ::-1, :]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        c = frame.sum(2)
        frame = cv2.cvtColor(frame[:,:,::-1], cv2.COLOR_BGR2RGBA).astype('float')
        x = (255-gray)/255
        x = self.a*(x - 0.5) + self.b
        mm = (c < 50)*255
        self.mask = self.mask*0.5 + 0.5*((np.tanh(x) + 1)/2 * 255) #+ 0.1 * mm
        frame[:, :, 0] *= self.mask/255
        frame[:, :, 1] *= self.mask/255
        frame[:, :, 2] *= self.mask/255
        frame[:, :, 3] = self.mask
        frame = frame.astype('uint8')
        H, W, _C = frame.shape

        scale = max(w/W, h/H)

        frame = cv2.resize(frame, (int(W*scale),int(H*scale)))

        img = frame
        H, W, C = img.shape

        data = img
        if self.surface is None or len(self.surface.get_data()) != len(data.flatten()):
            self.surface = cairo.ImageSurface.create_for_data(
                            data, cairo.FORMAT_ARGB32, W, H)

        else:
            buf = np.frombuffer(self.surface.get_data(), dtype='uint8')
            np.copyto(buf, data.flatten())

        context.set_source_rgba(0, 0, 0, 0)
        context.set_operator(cairo.OPERATOR_SOURCE)
        context.paint()
        context.set_operator(cairo.OPERATOR_OVER)
        context.set_source_surface(self.surface, 0, 0)
        context.paint()
        self.queue_draw()

win = TransparentWindow()
Gtk.main()
```
