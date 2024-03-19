---
layout: post
title:  "Fixing the posix Batch job scheduler by updating its load average limit"
date:   2019-07-19 23:02:00 +0200
categories: tech
comments: true
---

`batch(1)` is a little known posix command that
supposedly takes a list of jobs/shell scripts and executes them when the load average of the computer drops below a certain level.
It's far from an ideal scheduler, but it's builtin and does what is should do.
Problem is, the queued commands actually do not execute sometimes.
The load average limit is 1.5 by default,
but I have 6 cores/12 threads, so my load average rises easily above that.


The `atd(8)` daemon is responsible for job execution.
Add `-l $(your_load_limit)` to the `atd` invocation in `/etc/systemd/system/multi-user.target.wants/atd.service`
(which is a symlink to `/lib/systemd/system/atd.service` on my system),
or use the following shell commands to create a copy with the right configuration.


```
$ sed '/^ExecStart/s/$/ -l '$((`nproc`-1))/ /lib/systemd/system/atd.service | \
    sudo tee /etc/systemd/system/atd-replace.service
[Unit]
Description=Deferred execution scheduler
Documentation=man:atd(8)

[Service]
ExecStart=/usr/sbin/atd -f -l 11
IgnoreSIGPIPE=false

[Install]
WantedBy=multi-user.target
$ sudo systemctl stop atd.service
$ sudo systemctl disable atd.service
$ sudo systemctl enable atd-replace.service
$ sudo systemctl start atd-replace.service
```
