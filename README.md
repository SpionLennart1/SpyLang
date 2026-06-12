## SpyLang Commands

### Variables

**Create or update a variable**

```spy
LET name = value
```

Example:

```spy
LET hp = 100
LET username = "Player"
```

**Use a variable in text**

```spy
PRINT %username%
```

---

### Printing

**Print text or values**

```spy
PRINT "Hello world"
PRINT %hp%
```

**Colored output**

```spy
PRINT RED "Error"
PRINT GREEN "Success"
PRINT YELLOW "Warning"
PRINT BLUE "Info"
```

---

### Input

**Ask the user for input**

```spy
INPUT variable
```

Example:

```spy
PRINT "Enter your name:"
INPUT name
PRINT "Hello %name%"
```

---

### Math

SpyLang supports basic math expressions:

```spy
LET x = 5 + 10
LET y = 20 - 3
LET z = 4 * 5
LET a = 10 / 2
LET b = 10 % 3
LET c = (5 + 10) * 2
```

Supported operators:

* `+` addition
* `-` subtraction
* `*` multiplication
* `/` division
* `%` modulo
* `( )` parentheses

---

### Random Numbers

**Generate a random number**

```spy
LET roll = RANDOM 1 6
```

Example:

```spy
LET dice = RANDOM 1 6
PRINT %dice%
```

---

### Conditions

**IF statement**

```spy
IF condition {
    PRINT "True"
}
```

Example:

```spy
IF hp > 0 {
    PRINT "Alive"
}
```

**IF / ELSE**

```spy
IF age >= 18 {
    PRINT "Access granted"
}
ELSE {
    PRINT "Access denied"
}
```

**IF / ELSEIF / ELSE**

```spy
IF score >= 100 {
    PRINT "Perfect"
}
ELSEIF score >= 50 {
    PRINT "Good"
}
ELSE {
    PRINT "Try again"
}
```

Supported comparison operators:

* `==` equal
* `!=` not equal
* `>` greater than
* `<` less than
* `>=` greater or equal
* `<=` less or equal

---

### Loops

**WHILE loop**

```spy
WHILE condition {
    PRINT "Looping"
}
```

Example:

```spy
LET i = 0

WHILE i < 5 {
    PRINT %i%
    LET i = i + 1
}
```

**BREAK**

Stops the current loop.

```spy
WHILE 1 == 1 {
    INPUT answer

    IF answer == "exit" {
        BREAK
    }
}
```

---

### Functions

**Create a function**

```spy
FUNC name {
    PRINT "Hello"
}
```

**Call a function**

```spy
CALL name
```

Example:

```spy
FUNC hello {
    PRINT "Hello from a function!"
}

CALL hello
```

**Function parameters**

```spy
FUNC greet name {
    PRINT "Hello %name%"
}

CALL greet "Alex"
```

**Return values**

```spy
FUNC add a b {
    LET result = a + b
    RETURN result
}

CALL add 5 10
PRINT %__return__%
```

---

### Arrays

**Create an array**

```spy
LET inventory = [Sword,Shield,Potion]
```

**Multi-line arrays**

```spy
LET inventory = [
Sword,
Shield,
Potion
]
```

**Access array items**

```spy
PRINT inventory[0]
PRINT inventory[1]
PRINT inventory[2]
```

**Get array length**

```spy
PRINT LEN inventory
```

**Add an item to an array**

```spy
PUSH inventory "Bow"
```

**Remove the last item from an array**

```spy
POP inventory
```

---

### Files and Imports

**Import another SpyLang file**

```spy
IMPORT file.spy
```

Example:

```spy
IMPORT login.spy

CALL login
```

---

### Terminal Commands

**Clear the screen**

```spy
CLS
```

**Pause until Enter is pressed**

```spy
PAUSE
```

**Wait for a number of seconds**

```spy
SLEEP 2
```

---

### Networking / LAN Multiplayer

SpyLang supports simple LAN socket multiplayer.

**Host a connection**

```spy
HOST 5000
```

**Connect to a host**

```spy
CONNECT 127.0.0.1 5000
```

For LAN multiplayer, use the host computer's local IP address.

**Send a message or value**

```spy
SEND "hello"
SEND username
```

**Receive a message into a variable**

```spy
RECEIVE msg
PRINT %msg%
```

**Disconnect**

```spy
DISCONNECT
```

**Get your local IP**

```spy
PRINT %myip%
```

**Connection status**

```spy
IF netok == 1 {
    PRINT GREEN "Connected"
}
ELSE {
    PRINT RED "Connection failed"
}
```

---

### Comments

Lines starting with `#` are ignored.

```spy
# This is a comment
PRINT "Hello"
```

---

## Example Program

```spy
CLS

PRINT GREEN "SpyLang Demo"

LET hp = 100
LET roll = RANDOM 1 6

PRINT "You rolled:"
PRINT %roll%

IF roll == 6 {
    PRINT GREEN "Critical roll!"
}
ELSE {
    PRINT YELLOW "Normal roll."
}

PAUSE
```
