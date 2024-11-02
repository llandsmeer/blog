---
layout: post
title:  "Light/dark background in VIM based on current Konsole theme"
date:   2024-11-01T19:25:58.997994+00:00
categories: tech
status: published
---

I run konsole, tmux, and edit files in (neo)vim.
When switching themes in konsole, the background changes - and that can make the current colorscheme in vim very ugly.
Vim has a nice option called `background` that you can set to either `dark` or `light` based on the current terminal background.
It does not detect that, you have to set it manually.


Konsole supports exporting environment variables for each theme, which could make that, in theory easier.
Now tmux complicates the story again. The current terminal does not correspond to any shell konsole is aware of, and you could even have a light-themed and dark-themed konsole window open pointed to the same terminal.
From within tmux, I also haven't found a way to read the client's parent process' environment variables, and I couldn't even see them reflected in any process listed in /proc after a change.
So I found a quick hack:

For each theme, add an environment variable called 'KONSOLEBG' with as value light or dark.

Then update

### init.vim

```vim
if trim(system("colorscheme")) == "dark"
    set background=dark
else
    set background=light
endif
```

and create a binary somewhere (could also do this in the system() call I guess)

### ~/.local/bin/colorscheme (chmod +x)

```sh
#!/usr/bin/env bash

QT_SELECT=qt5 qdbus \
    org.kde.konsole-$(xdotool getactivewindow getwindowpid) \
    $KONSOLE_DBUS_SESSION \
    org.kde.konsole.Session.environment \
    | grep 'KONSOLEBG=' | cut -f 2 -d =
```

which contains:

 - `QT_SELECT=qt5` without that I would get an error message `qdbus: could not find a Qt installation of ''`
 - qdbus the dbus communication tool. invoked as `qdbus [servicename] [path] [method]`
 - servicename `org.kde.konsole-$(xdotool getactivewindow getwindowpid)`, i.e. konsole instance based on the active window pid. Using the environment variable would result in using the konsole session from the tmux server zsh, which might not even exist anymore
 - path: `$KONSOLE_DBUS_SESSION`
 - method:  `org.kde.konsole.Session.environment`, which lists the environment variables from the current profile



# Alternatives

Thus full list of methods is listed below, which could also give you some hints on how to implement this differently (eg.
eg. via `org.kde.konsole.Session.profile`)



```
method QByteArray org.kde.konsole.Session.codec()
method QStringList org.kde.konsole.Session.environment()
method bool org.kde.konsole.Session.flowControlEnabled()
method int org.kde.konsole.Session.foregroundProcessId()
method int org.kde.konsole.Session.historySize()
method bool org.kde.konsole.Session.isMonitorActivity()
method bool org.kde.konsole.Session.isMonitorSilence()
method int org.kde.konsole.Session.processId()
method QString org.kde.konsole.Session.profile()
method void org.kde.konsole.Session.runCommand(QString command)
method void org.kde.konsole.Session.sendMouseEvent(int buttons, int column, int line, int eventType)
method void org.kde.konsole.Session.sendText(QString text)
method bool org.kde.konsole.Session.setCodec(QByteArray name)
method void org.kde.konsole.Session.setEnvironment(QStringList environment)
method void org.kde.konsole.Session.setFlowControlEnabled(bool enabled)
method void org.kde.konsole.Session.setHistorySize(int lines)
method void org.kde.konsole.Session.setMonitorActivity(bool)
method void org.kde.konsole.Session.setMonitorSilence(bool)
method void org.kde.konsole.Session.setMonitorSilenceSeconds(int seconds)
method void org.kde.konsole.Session.setProfile(QString profileName)
method void org.kde.konsole.Session.setTabTitleFormat(int context, QString format)
method void org.kde.konsole.Session.setTitle(int role, QString title)
method QString org.kde.konsole.Session.shellSessionId()
method QString org.kde.konsole.Session.tabTitleFormat(int context)
method QString org.kde.konsole.Session.title(int role)
signal void org.freedesktop.DBus.Properties.PropertiesChanged(QString interface_name, QVariantMap changed_properties, QStringList invalidated_properties)
method QDBusVariant org.freedesktop.DBus.Properties.Get(QString interface_name, QString property_name)
method QVariantMap org.freedesktop.DBus.Properties.GetAll(QString interface_name)
method void org.freedesktop.DBus.Properties.Set(QString interface_name, QString property_name, QDBusVariant value)
method QString org.freedesktop.DBus.Introspectable.Introspect()
method QString org.freedesktop.DBus.Peer.GetMachineId()
method void org.freedesktop.DBus.Peer.Ping()
```
