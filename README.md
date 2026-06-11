📘 SpyLang Command List

🧠 VARIABLES
LET x = value        → create/change variable
Use variables: %x%

---

💬 INPUT / OUTPUT
PRINT value          → print text or numbers
PRINT RED "text"     → colored text
PRINT GREEN "text"
PRINT YELLOW "text"
PRINT BLUE "text"
INPUT x              → user input into variable

---

🔁 CONDITIONS
IF a == b { ... }    → run code if true

Operators:
==  equal
!=  not equal
> greater than
<   less than
>=  greater or equal
<=  less or equal

---

🔄 LOOPS
WHILE condition { ... } → repeat while true

Example:
WHILE x < 5 { ... }

---

🧩 FUNCTIONS
FUNC name { ... }        → define function
CALL name                → run function
CALL name a b           → pass arguments

---

🔙 RETURN
RETURN value            → exit function
Use result: __return__

---

📦 FILES
IMPORT file.spy         → load another file

---

🧹 SYSTEM COMMANDS
CLS      → clear screen
PAUSE    → wait for Enter
SLEEP 2  → wait 2 seconds

---

➗ MATH
Supports:
+  -  *  /
( ) parentheses

Example:
LET x = 5 + 10 * 2

---

💡 NOTES
• Variables are global unless inside functions
• Functions support parameters
• Keep syntax clean for best results
