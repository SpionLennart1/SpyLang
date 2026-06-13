# SpyLang

SpyLang is an experimental scripting language written in Python.

It is built for learning, terminal programs, small games, RPG demos, offline AI experiments, and simple LAN multiplayer projects.

SpyLang has grown from a basic scripting language into a small terminal game framework with arrays, objects, functions, save systems, offline AI, tile maps, quests, shops, enemies, timers, screen drawing, and multiplayer helper commands.

---

## Current Version

**SpyLang v2.5-game-framework-prerelease1**

Status: **Prerelease**

---

## What Is SpyLang?

SpyLang is a hobby programming language project made for writing simple scripts and terminal games.

Example:

```spy
PRINT GREEN "Welcome to SpyLang!"

LET player = {name:"Agent",stats:{hp:100,level:1},gold:50}

PRINT player.name
PRINT player.stats.hp
```

---

## Main Features

### Core Language

* Variables
* Strings
* Numbers
* Booleans
* Math expressions
* Conditions
* Loops
* Functions
* Function parameters
* Return values
* Global variables
* Imports
* Comments
* Line-number errors
* Arrays
* Objects / dictionaries
* Nested object access
* Nested object setting

### Game Framework

* Tile maps
* Player movement
* Collision checks
* Tile reading and writing
* Map transitions
* Distance checks
* Inventory helpers
* Dice rolls
* Timers
* Screen drawing
* Save slots
* Account saves
* Quests
* XP / level system
* Shops
* Enemy entity system

### Offline AI

* Random AI choices
* Percent chances
* Weighted decisions
* AI presets
* AI patrol routes
* AI chase/flee directions
* AI names
* AI dialogue
* AI personalities
* AI memory

### Multiplayer Helpers

* Host / connect
* Send / receive
* Try receive
* Receive timeout
* Ping
* Broadcast
* Disconnect
* Lobby helpers
* Turn helpers
* Username helpers
* Chat message helpers
* Network status helpers

### Launcher

SpyLang includes a launcher with:

* Embedded console
* Input bar
* Copy/paste support
* Responsive layout
* Fixed input bar
* Script list
* Built-in editor
* Basic syntax highlighting
* Error helper tools

---

## Requirements

You need **Python 3** installed.

Check Python:

```bash
py --version
```

or:

```bash
python --version
```

---

## How To Run SpyLang

Run a `.spy` file with:

```bash
py spy.py yourfile.spy
```

Example:

```bash
py spy.py debug.spy
```

---

## Launcher

Recommended launcher file:

```text
SpyLang_Launcher.pyw
```

Put it in the same folder as:

```text
spy.py
```

Then double-click the launcher.

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
IF hp > 0 {
    PRINT "Alive"
}
ELSE {
    PRINT "Dead"
}
```

```spy
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

SpyLang supports objects.

```spy
LET player = {name:"Agent",hp:100,gold:50}

PRINT player.name
PRINT player.hp
```

Nested objects:

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

Save slot menu:

```spy
SLOTMENU slots
PRINT %slots%
```

---

## Account System

SpyLang v2.5 includes a simple account save system for demos.

```spy
ACCOUNTCREATE player1 pass123 created
ACCOUNTLOGIN player1 pass123 login_ok

ACCOUNTSET player1 score 999
ACCOUNTGET player1 score score

ACCOUNTLIST accounts
ACCOUNTDELETE player1 deleted
```

This is for game/demo saves only. It is not meant for real security.

---

## Tile Maps

Create a map:

```spy
LET map = [
"#######",
"#P..E.#",
"#..#..#",
"#.....#",
"#######"
]
```

Draw the map:

```spy
DRAWMAP map
```

Find positions:

```spy
FINDPOS map "P" px py
FINDPOS map "E" ex ey
```

Read/write tiles:

```spy
GETTILE map px py tile
SETTILE map px py "."
```

Map size:

```spy
MAPSIZE map width height
```

Movement:

```spy
MOVEPLAYER map px py "d" moved
```

Collision check:

```spy
CANMOVE map 2 1 can_move
```

Distance:

```spy
DISTANCE px py ex ey dist
```

Map transition:

```spy
MAPTRANS 3 1 3 1 map_two 1 1 current_map new_x new_y
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

## Dice

```spy
DICE 2 6 roll

PRINT "2d6 roll:"
PRINT %roll%
```

The individual rolls are also saved in:

```spy
roll_rolls
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

## Quest System

```spy
QUESTADD main "Find the key"
QUESTSTATUS main done

PRINT %done%

QUESTDONE main
QUESTSTATUS main done

PRINT %done%

QUESTLIST quests
```

---

## XP / Level System

```spy
LET xp = 0
LET level = 1

XPADD xp level 250 leveled

PRINT "XP:"
PRINT %xp%

PRINT "Level:"
PRINT %level%

PRINT "Leveled up:"
PRINT %leveled%

LEVELINFO xp level needed
PRINT "XP needed:"
PRINT %needed%
```

---

## Shop System

Buy item:

```spy
LET gold = 50
LET inventory = []

SHOPBUY gold 20 "Potion" inventory bought

PRINT %bought%
PRINT %gold%
PRINT %inventory%
```

Sell item:

```spy
SHOPSELL inventory "Potion" 10 gold sold

PRINT %sold%
PRINT %gold%
```

---

## Enemy Entity System

Create an enemy:

```spy
ENEMYNEW Goblin 40 7 3 1 enemy
```

This creates an object like:

```text
enemy.name
enemy.hp
enemy.damage
enemy.x
enemy.y
```

Hit enemy:

```spy
ENEMYHIT enemy 15 enemy_dead
```

Check alive:

```spy
ENEMYALIVE enemy enemy_alive
```

Enemy attacks:

```spy
LET player_hp = 100

ENEMYATTACK enemy player_hp damage_done

PRINT %player_hp%
PRINT %damage_done%
```

Enemy movement:

```spy
ENEMYMOVE enemy map "a" enemy_moved
```

---

## Offline AI

### AICHOICE

```spy
LET moves = [Attack,Shield,Heal]

AICHOICE moves enemy_move

PRINT %enemy_move%
```

### AICHANCE

```spy
AICHANCE 25 crit

IF crit == true {
    PRINT RED "Critical hit!"
}
```

### AIWEIGHTED

```spy
AIWEIGHTED [Attack:70,Shield:20,Heal:10] move

PRINT %move%
```

### AIPRESET

```spy
AIPRESET aggressive move
AIPRESET defensive move
AIPRESET boss move
```

### AIPATH

```spy
AIPATH enemy_x enemy_y player_x player_y direction
```

### AICHASE

```spy
AICHASE enemy_x enemy_y player_x player_y direction
```

### AIFLEE

```spy
AIFLEE enemy_x enemy_y player_x player_y direction
```

### AIPATROL

```spy
AIPATROL [left,right] guard_path direction
```

### AIDIALOGUE

```spy
LET lines = ["Hello agent.","You look suspicious.","Buy something or leave."]

AIDIALOGUE lines npc_line

PRINT %npc_line%
```

### AINAME

```spy
AINAME spy npc_name
PRINT %npc_name%
```

### AIPERSONALITY

```spy
AIPERSONALITY funny line
PRINT %line%
```

### AI Memory

```spy
AIREMEMBER hero "Agent"
AIRECALL hero remembered
AIFORGET hero
```

---

## Multiplayer

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

---

## Multiplayer Helper Commands

Lobby:

```spy
LOBBYADD Player1
LOBBYADD Player2
LOBBYLIST lobby
```

Turns:

```spy
TURNINIT lobby current_turn
ISTURN Player1 is_turn
NEXTTURN current_turn
```

Username/chat:

```spy
SETUSERNAME "Agent"
GETUSERNAME username

MAKECHAT "Agent" "Hello" chat_msg
CHATSEND "Hello"
CHATRECEIVE msg
```

Network info:

```spy
NETREADY ready
NETINFO
```

Real multiplayer still needs testing on another PC or with another user. Same-PC testing only proves that the script logic and socket basics work.

---

## Debug Test

The v2.5 debug file tests the new framework features.

Run:

```bash
py spy.py debug.spy
```

Expected result:

```text
Passed: 39
Failed: 0
ALL V2.5 TESTS PASSED
```

---

## Example Project Structure

```text
SpyLang/
├─ spy.py
├─ SpyLang_Launcher.pyw
├─ README.md
├─ LICENSE
├─ debug.spy
├─ examples/
│  ├─ v2_5_game_framework_demo.spy
│  ├─ v2_5_mini_rpg.spy
│  ├─ chat.spy
│  └─ spy_duel_online.spy
├─ saves/
└─ configs/
```

---

## Important Notes

SpyLang is experimental.

It is mainly made for:

* learning
* terminal games
* RPG demos
* LAN multiplayer experiments
* offline AI game behavior
* scripting practice

It is not intended for secure or production use yet.

Account systems, save systems, and multiplayer systems are for demos and hobby projects.

---

## License

This project is licensed under the MIT License.

See the `LICENSE` file for details.
