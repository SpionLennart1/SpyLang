# SpyLang

**Version:** v3.5 (2026-06-19)

SpyLang is an experimental scripting language built in Python for learning, terminal programs, small games, map-based demos, menu-driven scripts, and LAN multiplayer experiments.

SpyLang is **source-available**, not open source. You may create and publish your own `.spy` scripts, games, demos, and examples, but the SpyLang interpreter itself may not be redistributed or republished unless the license allows it.

---

## Current Version

```text
v3.5 (2026-06-19)
```

This version focuses on:

- stable launcher behavior
- working `CLS` inside the launcher console
- improved launcher/editor workflow
- map engine tools
- menu system
- event system
- better syntax checking
- better error output
- better support for real 2D terminal games

---

## Requirements

You need Python 3 installed.

Check Python:

```bash
py --version
```

or:

```bash
python --version
```

---

## Running A Script

Use:

```bash
py spy.py script.spy
```

Example:

```bash
py spy.py v3-test.spy
```

You can also use:

```text
SpyLang_Launcher.pyw
```

Keep the launcher in the same folder as:

```text
spy.py
```

---

## Launcher

The v3.5 launcher includes:

- Console tab
- Editor tab
- Scripts tab
- Settings tab
- Integrated editor
- Basic syntax highlighting
- Script cards
- Fixed input bar
- Copy/paste console output
- Error helper tools
- Stable Windows taskbar behavior
- Fixed `CLS` behavior inside the launcher console

---

## Hello World

```spy
PRINT "Hello world!"
```

Colored output:

```spy
PRINT GREEN "Success!"
PRINT RED "Error!"
PRINT YELLOW "Warning!"
PRINT BLUE "Info!"
```

---

## Variables

```spy
LET name = "Agent"
LET hp = 100
LET gold = 50

PRINT %name%
PRINT %hp%
PRINT %gold%
```

---

## Input

```spy
PRINT "Enter your name:"
INPUT name

PRINT "Welcome:"
PRINT %name%
```

---

## Math

```spy
LET a = 5 + 10
LET b = 20 - 3
LET c = 4 * 5
LET d = 10 / 2
LET e = 10 % 3
LET f = (5 + 10) * 2

PRINT %f%
```

Supported operators:

```text
+
-
*
/
%
( )
```

---

## Conditions

```spy
LET hp = 100

IF hp > 0 {
    PRINT "Alive"
}
ELSE {
    PRINT "Dead"
}
```

```spy
LET score = 75

IF score >= 100 {
    PRINT "Master"
}
ELSEIF score >= 50 {
    PRINT "Good"
}
ELSE {
    PRINT "Beginner"
}
```

---

## Loops

### WHILE

```spy
LET i = 0

WHILE i < 5 {
    PRINT %i%
    LET i = i + 1
}
```

### REPEAT

```spy
REPEAT 5 {
    PRINT "Hello"
}
```

### FOR

```spy
FOR i = 1 TO 10 {
    PRINT %i%
}
```

### FOR STEP

```spy
FOR i = 2 TO 10 STEP 2 {
    PRINT %i%
}
```

### FOREACH

```spy
LET items = [Sword,Shield,Potion]

FOREACH item items {
    PRINT %item%
}
```

---

## Functions

```spy
FUNC hello {
    PRINT "Hello from a function!"
}

CALL hello
```

Function with parameters:

```spy
FUNC greet name {
    PRINT "Hello:"
    PRINT %name%
}

CALL greet "Agent"
```

Return value:

```spy
FUNC add a b {
    LET result = a + b
    RETURN result
}

LET sum = CALL add 5 10

PRINT %sum%
```

Global variables:

```spy
LET score = 0

FUNC add_score {
    GLOBAL score
    LET score = score + 10
}

CALL add_score

PRINT %score%
```

---

## Arrays

```spy
LET inventory = [Sword,Shield,Potion]

PRINT inventory[0]
PRINT inventory[1]
PRINT inventory[2]
```

Array commands:

```spy
PUSH inventory "Key"
POP inventory
SET inventory[0] "Axe"
CLEAR inventory
PRINT LEN inventory
```

---

## Objects

```spy
LET player = {name:"Agent",hp:100,gold:50}

PRINT player.name
PRINT player.hp
```

Nested object example:

```spy
LET player = {name:"Agent",stats:{hp:100,level:1},gold:50}

PRINT player.stats.hp
SET player.stats.hp 80
PRINT player.stats.hp
```

Object commands:

```spy
NEWOBJ player
OBJSET player name "Agent"
OBJSET player hp 100
OBJGET player hp player_hp
OBJHAS player hp has_hp
OBJKEYS player keys
OBJDEL player hp
```

---

## Files And Saves

Save/load variable:

```spy
LET score = 100

SAVEVAR score "score.spsave"
LOADVAR loaded_score "score.spsave"

PRINT %loaded_score%
```

Write/read file:

```spy
WRITEFILE "note.txt" "Hello SpyLang"
READFILE "note.txt" message

PRINT %message%
```

Save slots:

```spy
SAVESLOT 1 player
LOADSLOT 1 player
LISTSLOTS slots
DELSLOT 1
```

---

## Utility Commands

```spy
CLS
PAUSE
SLEEP 1
WAITKEY
VERSION
```

String helpers:

```spy
LET upper_name = UPPER "agent"
LET lower_name = LOWER "AGENT"

IF "SpyLang" CONTAINS "Spy" {
    PRINT "Found it"
}
```

Random number:

```spy
RANDOM number 1 10
PRINT %number%
```

---

## Map Engine

SpyLang includes map tools for terminal games and map-based programs.

### Create A Map

```spy
MAPFILL 20 10 "." map
MAPBORDER map "#"
SETTILE map 1 1 "P"

DRAWMAP map
```

### Rectangle

```spy
MAPRECT map 5 3 6 4 "#"
DRAWMAP map
```

### Line

```spy
MAPLINE map 1 1 10 1 "#"
DRAWMAP map
```

### Replace Tiles

```spy
MAPREPLACE map "." ","
DRAWMAP map
```

### Count Tiles

```spy
MAPCOUNT map "#" wall_count
PRINT %wall_count%
```

### Find All Tiles

```spy
MAPFINDALL map "#" walls
PRINT %walls%
```

### Copy And Paste Maps

```spy
MAPCOPY map backup
MAPPASTE map backup 0 0
```

### Viewport

```spy
VIEWPORT map 0 0 10 5 view
DRAWMAP view
```

### Load And Save Maps

```spy
SAVEMAP "maps/level1.map" map
LOADMAP "maps/level1.map" loaded_map

DRAWMAP loaded_map
```

---

## Tile Commands

```spy
MAPSIZE map width height
GETTILE map x y tile
SETTILE map x y "."
FINDPOS map "P" px py
CANMOVE map x y can_move
MOVEPLAYER map px py "d" moved
DISTANCE px py ex ey dist
```

Example:

```spy
LET map = [
"#######",
"#P..E.#",
"#..#..#",
"#.....#",
"#######"
]

FINDPOS map "P" px py
MOVEPLAYER map px py "d" moved
DRAWMAP map
```

---

## Menu System

### Create And Show A Menu

```spy
MENUCREATE main_menu
MENUADD main_menu "Start Game"
MENUADD main_menu "Options"
MENUADD main_menu "Exit"

MENUSHOW main_menu choice

PRINT "Selected:"
PRINT %choice%
```

### Draw A Menu Without Choosing

```spy
MENUDRAW main_menu
```

### Count Menu Items

```spy
MENUCOUNT main_menu count
PRINT %count%
```

### Clear Menu

```spy
MENUCLEAR main_menu
```

### Select From A List

```spy
LET difficulties = [Easy,Medium,Hard,Nightmare]

SELECTLIST difficulties choice

PRINT "Difficulty:"
PRINT %choice%
```

### Confirm

```spy
CONFIRM "Are you sure?" result

IF result == true {
    PRINT "Confirmed"
}
ELSE {
    PRINT "Cancelled"
}
```

### Prompt

```spy
PROMPT "Enter your name" player_name

PRINT %player_name%
```

---

## Event System

Events are useful for game flags, doors, tutorials, cutscenes, one-time messages, unlocks, and other game logic.

### Set And Get Events

```spy
EVENTSET door_open false
EVENTGET door_open open

PRINT %open%
```

### Check If An Event Exists

```spy
EVENTEXISTS door_open exists
PRINT %exists%
```

### Trigger Event

```spy
TRIGGER intro_done
EVENTGET intro_done done

PRINT %done%
```

### One-Time Event

```spy
EVENTONCE tutorial_message first_time

IF first_time == true {
    PRINT "This only shows once."
}
```

### Clear Event

```spy
EVENTCLEAR door_open
```

### Run Function On Trigger

```spy
FUNC intro {
    PRINT "Intro started."
}

ONTRIGGER intro_event intro
```

---

## Screen Drawing

```spy
SCREENCLEAR
SCREENWRITE 0 0 "HP:"
SCREENWRITE 4 0 100
SCREENWRITE 0 1 "Gold:"
SCREENWRITE 6 1 50
SCREENRENDER
```

---

## Timers

```spy
TIMERSTART game_timer

SLEEP 1

TIMERGET game_timer seconds
PRINT %seconds%

TIMERRESET game_timer
```

---

## Dice

```spy
DICE 2 6 roll

PRINT "2d6 roll:"
PRINT %roll%
```

The individual rolls are also saved in:

```text
roll_rolls
```

---

## Inventory Helpers

```spy
LET inventory = [Potion]

ADDITEM inventory "Key"
HASITEM inventory "Key" has_key
COUNTITEM inventory "Key" key_count
REMOVEITEM inventory "Key" removed
```

---

## Basic Networking

SpyLang includes basic socket commands for LAN experiments.

Host:

```spy
HOST 5000
```

Connect:

```spy
CONNECT 127.0.0.1 5000
```

Send:

```spy
SEND "hello"
```

Receive:

```spy
RECEIVE msg
PRINT %msg%
```

Try receive:

```spy
TRYRECEIVE msg
```

Receive with timeout:

```spy
RECEIVE msg TIMEOUT 5
```

Ping:

```spy
PING
PRINT %netok%
```

Broadcast:

```spy
BROADCAST "hello everyone"
```

Disconnect:

```spy
DISCONNECT
```

Real LAN or internet multiplayer depends on firewall, router, Wi-Fi, and network setup.

---

## Example 2D Game Ideas

SpyLang can now handle more than simple dice games or enter-to-roll programs.

Good project ideas:

- dungeon crawler
- key and door puzzle game
- monster escape game
- turn-based battle map
- maze game
- shop and inventory game
- LAN chat program
- LAN turn-based game
- save-slot RPG prototype

---

## Test Result Example

A successful v3 test showed:

```text
Passed:
26
Failed:
0
ALL V3 TESTS PASSED
```

---

## Example Project Structure

```text
SpyLang/
├─ spy.py
├─ SpyLang_Launcher.pyw
├─ README.md
├─ LICENSE
├─ examples/
│  ├─ map-demo.spy
│  ├─ menu-demo.spy
│  └─ game-demo.spy
├─ saves/
├─ maps/
└─ configs/
```

---

## Important Notes

SpyLang is experimental.

It is mainly made for:

- learning
- terminal programs
- small terminal games
- map experiments
- menu-driven scripts
- LAN multiplayer experiments
- scripting practice

It is not intended for production use yet.

Save systems, account/demo systems, and networking systems are for hobby projects and testing.

---

## License

SpyLang uses a custom source-available license.

In general:

- users may create and publish their own `.spy` scripts
- users may create and publish their own games made as `.spy` files
- users may share demos and examples they wrote themselves
- users may not republish or redistribute the SpyLang interpreter itself unless the license allows it
- users may not publish modified interpreter releases as their own SpyLang version

See the `LICENSE` file for the full terms.
