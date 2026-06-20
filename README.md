# SpyLang

**Version:** v3.7 (2026-06-20)

SpyLang is an experimental scripting language built in Python for learning, terminal programs, small games, map-based demos, menu-driven scripts, and LAN multiplayer experiments.

SpyLang is **source-available**, not open source.

You may create, share, publish, and sell your own `.spy` scripts, games, demos, and examples. You may not redistribute, re-upload, republish, sell, sublicense, rebrand, or publish modified versions of the SpyLang interpreter unless the license allows it.

---

## Simple Folder Layout

This simple package only keeps the important stuff visible:

```text
SpyLang/
├─ spy.py
├─ SpyLang_Launcher.pyw
├─ START_HERE.spy
├─ v3-test.spy
├─ v3-test-helper.spy
├─ v37-test.json
├─ README.md
├─ LICENSE
└─ modules/
```

The `modules/` folder is the only folder you should keep. It is used by the new `INCLUDE` command.

`v37-test.json` is only used by `v3-test.spy` to test config loading.

---

## Start Here

Open:

```text
SpyLang_Launcher.pyw
```

Then run:

```text
START_HERE.spy
```

Or from terminal:

```bash
py spy.py START_HERE.spy
```

---

## Test SpyLang

Run:

```bash
py spy.py v3-test.spy
```

A good result looks like:

```text
Passed:
37
Failed:
0
ALL V3.7 TESTS PASSED
```

---

## Basic Example

```spy
print "Hello world!"

let name = "Agent"
print %name%
```

Commands are not case-sensitive:

```spy
PRINT "Hello"
print "Hello"
Print "Hello"
```

Variable names, strings, paths, function names, and object keys keep their original casing.

---

## INCLUDE

`INCLUDE` loads a module from the `modules/` folder.

```spy
INCLUDE inventory
```

That loads:

```text
modules/inventory.spy
```

It works like an easier `IMPORTONCE`.

---

## PROJECTINFO

Print project/script information:

```spy
PROJECTINFO
```

Save project info into an object:

```spy
PROJECTINFO project
PRINT project.version
PRINT project.script
PRINT project.folder
```

---

## Config Commands

```spy
CONFIGLOAD "config.json" config
CONFIGGET config "title" game_title
```

---

## Log Commands

```spy
LOG "Game started"
WARN "Low health"
ERROR "Something went wrong"
```

---

## Important Commands

```text
LET, PRINT, INPUT, IF, ELSEIF, ELSE, WHILE, REPEAT, FOR, FOREACH
FUNC, CALL, RETURN, GLOBAL
PUSH, POP, SET, DEL, CLEAR
SAVEVAR, LOADVAR, WRITEFILE, READFILE
IMPORT, IMPORTONCE, INCLUDE
PROJECTINFO, CONFIGLOAD, CONFIGGET
LOG, WARN, ERROR, DEBUG, ASSERT, DUMPVAR, DUMPVARS
CLS, PAUSE, SLEEP, WAITKEY, VERSION
HOST, CONNECT, SEND, RECEIVE, TRYRECEIVE, BROADCAST, PING, DISCONNECT
MAPFILL, MAPBORDER, MAPRECT, MAPLINE, MAPCOPY, MAPPASTE, MAPREPLACE
MAPCOUNT, MAPFINDALL, VIEWPORT, LOADMAP, SAVEMAP
MENUCREATE, MENUADD, MENUCLEAR, MENUDRAW, MENUCOUNT, MENUSHOW
SELECTLIST, CONFIRM, PROMPT
EVENTSET, EVENTGET, EVENTCLEAR, EVENTEXISTS, EVENTONCE, TRIGGER, ONTRIGGER
```

---

## Notes

SpyLang is experimental and mainly made for learning, terminal games, scripting practice, and LAN experiments.

Networking depends on firewall, router, Wi-Fi, and network setup.

See `LICENSE` for the full custom source-available license.
