# SpyLang

SpyLang is an experimental scripting language written in Python.

It is made for learning, testing, terminal programs, small games, and simple LAN multiplayer projects.

SpyLang is still experimental, but it now supports variables, math, functions, arrays, loops, file saving/loading, imports, colored output, and socket-based multiplayer.

---

## Current Version

**SpyLang v1.6**

---

## Features

### Core Language

- Variables
- Math expressions
- Strings
- Booleans
- Conditions
- Loops
- Functions
- Return values
- Global variables from functions
- Comments
- Imports
- Better error messages
- `EXIT`
- `BREAK`

### Arrays

- One-line arrays
- Multi-line arrays
- Array indexing
- `SET array[index] value`
- `PUSH`
- `POP`
- `CLEAR`
- `LEN`
- `FOREACH`

### Terminal Features

- Colored output
- `CLS`
- `PAUSE`
- `SLEEP`
- `WAITKEY`

### Files / Saves

- Save variables
- Load variables
- Write files
- Read files
- Save games
- High scores
- Config files

### Networking

SpyLang supports simple LAN multiplayer using sockets.

- Host games
- Join games
- Send messages
- Receive messages
- Try receiving without freezing
- Receive with timeout
- Ping connection
- Broadcast messages
- Multiple clients support

---

## Requirements

You need **Python 3** installed.

Recommended:

```bash
python --version
```

or on Windows:

```bash
py --version
```

---

## How To Run SpyLang

Run a `.spy` file with:

```bash
py spy.py yourfile.spy
```

Example:

```bash
py spy.py examples/hello.spy
```

---

## SpyLang Launcher

SpyLang also includes a `.pyw` launcher.

The launcher lets you:

- Select `.spy` files
- Run scripts in an embedded console
- Use an input bar for `INPUT`
- Use `WAITKEY` through the input bar
- Search scripts
- Open scripts in Notepad
- Create starter files
- Keep launcher configs inside the `configs/` folder

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

Create variables with `LET`.

```spy
LET name = "Agent"
LET hp = 100
LET score = 0
```

Print variables:

```spy
PRINT %name%
PRINT %hp%
```

---

## Input

Ask the user for input:

```spy
PRINT "Enter your name:"
INPUT name

PRINT "Welcome:"
PRINT %name%
```

---

## Math

SpyLang supports math expressions.

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

## Booleans

SpyLang supports `true` and `false`.

```spy
LET alive = true
LET banned = false

IF alive == true {
    PRINT "Player is alive."
}
```

---

## Conditions

### IF

```spy
IF hp > 0 {
    PRINT "Alive"
}
```

### IF / ELSE

```spy
IF age >= 18 {
    PRINT "Access granted"
}
ELSE {
    PRINT "Access denied"
}
```

### IF / ELSEIF / ELSE

```spy
IF score >= 90 {
    PRINT "Master"
}
ELSEIF score >= 50 {
    PRINT "Coder"
}
ELSE {
    PRINT "Beginner"
}
```

Supported comparison operators:

```text
==
!=
>
<
>=
<=
```

---

## CONTAINS

Check if text contains something:

```spy
LET message = "SpyLang is cool"

IF message CONTAINS "cool" {
    PRINT GREEN "Found word!"
}
```

---

## String Helpers

### UPPER

```spy
LET name = "spylang"
LET big = UPPER name

PRINT %big%
```

Output:

```text
SPYLANG
```

### LOWER

```spy
LET name = "SPYLANG"
LET small = LOWER name

PRINT %small%
```

Output:

```text
spylang
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

### BREAK

`BREAK` stops the current loop.

```spy
LET i = 0

WHILE i < 10 {
    PRINT %i%

    IF i == 4 {
        BREAK
    }

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

---

## Functions

Create a function with `FUNC`.

```spy
FUNC hello {
    PRINT "Hello from a function!"
}

CALL hello
```

---

## Function Parameters

```spy
FUNC greet name {
    PRINT "Hello:"
    PRINT %name%
}

CALL greet "Alex"
```

---

## Return Values

Functions can return values.

```spy
FUNC add a b {
    LET result = a + b
    RETURN result
}

LET sum = CALL add 5 10

PRINT %sum%
```

Output:

```text
15
```

---

## Global Variables From Functions

Use `GLOBAL` to let a function change a variable outside the function.

```spy
LET score = 0

FUNC add_score {
    GLOBAL score
    LET score = score + 10
}

CALL add_score

PRINT %score%
```

Output:

```text
10
```

---

## Arrays

Create an array:

```spy
LET inventory = [Sword,Shield,Potion]
```

Print array items:

```spy
PRINT inventory[0]
PRINT inventory[1]
PRINT inventory[2]
```

Arrays start at index `0`.

---

## Multi-Line Arrays

```spy
LET weapons = [
Knife,
Pistol,
Rifle
]
```

---

## Array Length

```spy
PRINT LEN inventory
```

---

## PUSH

Add an item to an array:

```spy
PUSH inventory "Bow"
```

---

## POP

Remove the last item from an array:

```spy
POP inventory
```

---

## SET Array Item

Change an item in an array:

```spy
SET inventory[0] "Axe"
```

Example:

```spy
LET inventory = [Sword,Shield,Potion]

SET inventory[1] "Bow"

PRINT inventory[1]
```

Output:

```text
Bow
```

---

## CLEAR Array

Clear an array:

```spy
CLEAR inventory
```

---

## FOREACH

Loop through an array:

```spy
LET inventory = [Sword,Shield,Potion]

FOREACH item inventory {
    PRINT %item%
}
```

---

## DEL Variable

Delete a variable:

```spy
LET temp = "delete me"

DEL temp
```

---

## Random Numbers

Generate a random number:

```spy
LET dice = RANDOM 1 6

PRINT %dice%
```

---

## Terminal Commands

### CLS

Clear the screen:

```spy
CLS
```

### PAUSE

Wait for Enter:

```spy
PAUSE
```

### SLEEP

Wait for seconds:

```spy
SLEEP 2
```

### WAITKEY

Wait for one key:

```spy
WAITKEY key

PRINT "You pressed:"
PRINT %key%
```

In the launcher, `WAITKEY` uses the input bar. Type one key and press Enter.

---

## EXIT

Stop the whole script:

```spy
PRINT "Before exit"

EXIT

PRINT "This will not print"
```

---

## Comments

Comments start with `#`.

```spy
# This is a comment
PRINT "Hello"
```

Inline comments are also supported:

```spy
LET hp = 100 # player health
```

---

## Imports

Import another `.spy` file:

```spy
IMPORT debug.spy

CALL debug
```

Example project:

```text
SpyLang/
├─ spy.py
├─ main.spy
└─ debug.spy
```

`main.spy`:

```spy
IMPORT debug.spy

CALL debug
```

---

## Save And Load Variables

### SAVEVAR

```spy
LET score = 100

SAVEVAR score "score.spsave"
```

### LOADVAR

```spy
LOADVAR score "score.spsave"

PRINT %score%
```

---

## Write And Read Files

### WRITEFILE

```spy
WRITEFILE "note.txt" "Hello from SpyLang"
```

### READFILE

```spy
READFILE "note.txt" message

PRINT %message%
```

---

## Networking / LAN Multiplayer

SpyLang supports socket-based LAN multiplayer.

### HOST

Start a server:

```spy
HOST 5000
```

Host with multiple clients:

```spy
HOST 5000 4
```

### CONNECT

Connect to a host:

```spy
CONNECT 127.0.0.1 5000
```

For same-PC testing, use:

```text
127.0.0.1
```

For LAN testing, use the host computer's local IP.

SpyLang provides your local IP in:

```spy
PRINT %myip%
```

---

## SEND

Send a message or value:

```spy
SEND "hello"
SEND username
SEND score
```

---

## RECEIVE

Receive a message into a variable:

```spy
RECEIVE msg

PRINT %msg%
```

---

## RECEIVE TIMEOUT

Wait for a message with a timeout:

```spy
RECEIVE msg TIMEOUT 5
```

---

## TRYRECEIVE

Try to receive without freezing forever:

```spy
TRYRECEIVE msg
```

---

## PING

Check connection status:

```spy
PING

IF netok == 1 {
    PRINT GREEN "Connected"
}
ELSE {
    PRINT RED "Not connected"
}
```

---

## BROADCAST

Send a message to all connected clients:

```spy
BROADCAST "hello everyone"
```

---

## DISCONNECT

Close the connection:

```spy
DISCONNECT
```

---

## Network Variables

SpyLang uses these built-in networking variables:

```text
myip
netok
netmsg
netclient
```

### myip

Your local IP address.

```spy
PRINT %myip%
```

### netok

Connection status.

```text
1 = ok
0 = failed / not connected
```

### netmsg

Message receive status.

```text
1 = message received
0 = no message
```

### netclient

Client index for multi-client receiving.

---

## Simple Host Example

```spy
PRINT "Hosting..."
PRINT "Your IP:"
PRINT %myip%

HOST 5000

RECEIVE msg

PRINT "Client said:"
PRINT %msg%

SEND "Hello client!"

DISCONNECT
```

---

## Simple Client Example

```spy
PRINT "Enter host IP:"
INPUT ip

CONNECT ip 5000

SEND "Hello host!"

RECEIVE reply

PRINT "Host replied:"
PRINT %reply%

DISCONNECT
```

---

## Example Program

```spy
CLS

PRINT GREEN "SpyLang Demo"

LET hp = 100
LET dice = RANDOM 1 6

PRINT "You rolled:"
PRINT %dice%

IF dice == 6 {
    PRINT GREEN "Critical roll!"
}
ELSE {
    PRINT YELLOW "Normal roll."
}

PAUSE
```

---

## Debug Test

SpyLang includes a debug file for testing language features.

Example:

```spy
IMPORT debug.spy

CALL debug
```

The debug file tests:

- Math
- Variables
- Conditions
- Loops
- Functions
- Arrays
- `SET`
- `FOREACH`
- `REPEAT`
- `FOR`
- `GLOBAL`
- Save/load
- File read/write
- `WAITKEY`
- Networking basics

---

## Example Folder Structure

Recommended project structure:

```text
SpyLang/
├─ spy.py
├─ SpyLang_Launcher.pyw
├─ README.md
├─ debug.spy
├─ configs/
│  └─ spylang_launcher_config.json
├─ examples/
│  ├─ hello.spy
│  ├─ tutorial_quiz.spy
│  ├─ spy_duel_online.spy
│  └─ chat.spy
└─ saves/
   └─ score.spsave
```

---

## GitHub Update Workflow

After editing files locally:

```bash
git status
git add -A
git commit -m "Update SpyLang"
git push
```

Nothing is uploaded to GitHub until you run:

```bash
git push
```

---

## Important Notes

SpyLang is experimental.

It is mainly made for:

- learning
- testing
- small terminal apps
- small games
- LAN multiplayer demos

It is not intended for secure or production use yet.

Login systems, age verification, and account systems made in SpyLang are for demos only and should not be used as real security.

---

## License

Add your license here.

Example:

```text
MIT License
```

---

## Credits

Created by Lennart Wiechers.

SpyLang is a hobby programming language project built for learning, experimenting, and making fun terminal programs.