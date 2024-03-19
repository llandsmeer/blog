---
layout: post
title:  "Running SLURM locally on Ubuntu 18.04"
date:   2020-03-02 15:43:00 +0100
categories: tech
comments: true
---

Today I found myself needing to set up a minimal SLURM cluster
on my laptop for simple testing purposes.
As always, there were some challenges along the way
and I had to consult multiple installation guides and stackoverflow questions
to make everything fit together.
Here is what worked for me.

## Set up munge

```
$ sudo apt install munge
```

Test if it works:

```
$ munge -n | unmunge
STATUS:           Success (0)
[...]
```

## Set up MariaDB

[From here](https://github.com/mknoxnv/ubuntu-slurm)

```
$ sudo apt install mariadb-server
$ sudo mysql -u root
create database slurm_acct_db;
create user 'slurm'@'localhost';
set password for 'slurm'@'localhost' = password('slurmdbpass');
grant usage on *.* to 'slurm'@'localhost';
grant all privileges on slurm_acct_db.* to 'slurm'@'localhost';
flush privileges;
exit
```

## Set up SLURM

```
$ sudo apt install slurmd slurm-client slurmctld
```

Use configurator.html to create the SLURM config file.
There is one oneline [here](https://slurm.schedmd.com/configurator.html)
but it is [only useful for the last version](https://stackoverflow.com/questions/53028499/setting-up-slurm-conf-file-for-single-computer).

Find out which version you have (`dpkg -l | grep slurm`, mine was 17.11.2). Go to
[https://www.schedmd.com/archives.php](https://www.schedmd.com/archives.php)
and download the package correspond to your version
(ended up with a small version mismatch, worked out anyway).

Unpack and enter directory, then build en run the Configuration Tool

```
$ cd slurm-17.11.10
$ ./configure
$ make html
$ xdg-open doc/html/configurator.html
```

 - Fill in all NodeName/Hostname field in with own `hostname(1)`.
 - For testing, fill in `root` for SlurmUser.
 - [Make sure](https://stackoverflow.com/questions/56553665/how-to-fix-slurmd-service-cant-open-pid-file-error-in-slurm)
   that the `slurmd` and `slurmctld` PID file path are the same as listed in the systemd file (`/lib/systemd/system/slurmd.service`).
 - You might want to look at the Number of CPUs setting
 - Copy-paste to `/etc/slurm-llnll/slurm.conf`.

Create a file `/etc/slurm-llnl/cgroup.conf`:

```
CgroupAutomount=yes
CgroupReleaseAgentDir="/etc/slurm/cgroup"
ConstrainCores=yes
ConstrainDevices=yes
ConstrainRAMSpace=yes
```

Restart daemons

```
sudo systemctl restart slurmctld
sudo systemctl restart slurmd
```

Running `sinfo` should show no errors:

```
$ sinfo
PARTITION AVAIL  TIMELIMIT  NODES  STATE NODELIST
debug*       up   infinite      1   idle a715
```

## Test an actual job

Run sleep 1 on 8 processors:

```
$ time srun -n8 sleep 1
srun -n8 sleep 1  -- 1,20s (0,01s(u) + 0,00s(s) 6kb 0+49 ctx)
```

## Some useful debugging commands

```
$ slurmctld -D
$ slurmd -D
$ sinfo
```

## Set up mail (optional)

Install postfix

```
$ sudo apt install postfix mailutils
```

Edit `/etc/postfix/main.cf` and change

```
inet_interfaces = loopback-only
```

Restart and test locally.

```
$ sudo systemctl restart slurmctld
$ sudo systemctl restart slurmd
$ srun --mail-type=ALL hostname
$ cat /var/mail/$(whoami)  | grep Subject
```

If everything went well, you should now have your own private computer cluster up and running :)
