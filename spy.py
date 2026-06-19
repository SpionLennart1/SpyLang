import sys
import operator
import os
import time
import random
import re
import socket
import select
import json
import difflib
import traceback

variables = {}
functions = {}
files_loaded = set()

net_server = None
net_conn = None
net_socket = None
net_clients = []

RETURN_SIGNAL = "__RETURN__"
BREAK_SIGNAL = "__BREAK__"
EXIT_SIGNAL = "__EXIT__"

SPYLANG_VERSION = "v3.5 (2026-06-19)"


# -----------------------------
# MATH PRECEDENCE
# -----------------------------
precedence = {
    "+": 1,
    "-": 1,
    "*": 2,
    "/": 2,
    "%": 2
}


# -----------------------------
# BASIC HELPERS
# -----------------------------
def make_lines(lines, filename="<script>"):
    made = []

    for idx, raw in enumerate(lines, start=1):
        if isinstance(raw, dict):
            made.append(raw)
        else:
            made.append({
                "text": str(raw).rstrip("\n"),
                "line": idx,
                "file": filename
            })

    return made


def get_text(line):
    if isinstance(line, dict):
        return line.get("text", "")
    return str(line)


def get_line_number(line):
    if isinstance(line, dict):
        return line.get("line", "?")
    return "?"


def get_filename(line):
    if isinstance(line, dict):
        return line.get("file", "<script>")
    return "<script>"


def strip_inline_comment(text):
    in_quote = False
    escaped = False
    out = ""

    for ch in str(text):
        if ch == "\\" and in_quote:
            escaped = not escaped
            out += ch
            continue

        if ch == '"' and not escaped:
            in_quote = not in_quote
            out += ch
            continue

        escaped = False

        if ch == "#" and not in_quote:
            break

        out += ch

    return out.rstrip()


def error(line_obj, message, suggestion=None):
    print("SpyLang error")
    print(f"File: {get_filename(line_obj)}")
    print(f"Line: {get_line_number(line_obj)}")
    raw_code = get_text(line_obj).strip()
    if raw_code:
        print("Code:")
        print(raw_code)
    print(message)
    if suggestion:
        print(suggestion)


def suggest_command(cmd):
    commands = [
        'LET', 'PRINT', 'INPUT', 'IF', 'ELSEIF', 'ELSE', 'WHILE', 'FOR', 'REPEAT', 'FOREACH', 'FUNC', 'CALL', 'RETURN', 'GLOBAL', 'BREAK', 'EXIT', 'PUSH', 'POP', 'SET', 'DEL', 'CLEAR', 'SAVEVAR',
        'LOADVAR', 'WRITEFILE', 'READFILE', 'CLS', 'PAUSE', 'SLEEP', 'WAITKEY', 'HOST', 'CONNECT', 'SEND', 'RECEIVE', 'TRYRECEIVE', 'BROADCAST', 'PING', 'DISCONNECT', 'IMPORT', 'AICHOICE', 'AICHANCE', 'AIWEIGHTED', 'AIDECIDE', 'AIREMEMBER', 'AIRECALL', 'AIFORGET', 'AIPATH', 'AISTATE',
        'AIDIALOGUE', 'AINAME', 'AIPERSONALITY', 'AIROUTE', 'AIPRESET', 'AIPATROL', 'AICHASE', 'AIFLEE', 'DRAWMAP', 'MAPSIZE', 'GETTILE', 'SETTILE', 'FINDPOS', 'CANMOVE', 'MOVEPLAYER', 'DISTANCE', 'MAPTRANS', 'LOADMAP', 'SAVEMAP', 'MAPFILL', 'MAPBORDER', 'MAPRECT', 'MAPLINE', 'MAPCOPY', 'MAPPASTE', 'MAPREPLACE', 'MAPCOUNT', 'MAPFINDALL', 'VIEWPORT', 'MENUCREATE', 'MENUADD', 'MENUCLEAR', 'MENUDRAW', 'MENUCOUNT', 'MENUSHOW', 'SELECTLIST', 'CONFIRM', 'PROMPT', 'EVENTSET', 'EVENTGET', 'EVENTCLEAR', 'EVENTEXISTS', 'EVENTONCE', 'TRIGGER', 'ONTRIGGER', 'NEWOBJ', 'OBJSET', 'OBJGET', 'OBJHAS', 'OBJDEL', 'OBJKEYS', 'SAVESLOT', 'LOADSLOT',
        'DELSLOT', 'LISTSLOTS', 'SLOTMENU', 'ACCOUNTCREATE', 'ACCOUNTLOGIN', 'ACCOUNTSET', 'ACCOUNTGET', 'ACCOUNTDELETE', 'ACCOUNTLIST', 'QUESTADD', 'QUESTDONE', 'QUESTSTATUS', 'QUESTLIST', 'XPADD', 'LEVELINFO', 'SHOPBUY', 'SHOPSELL', 'ENEMYNEW', 'ENEMYHIT', 'ENEMYALIVE', 'ENEMYATTACK', 'ENEMYMOVE', 'TIMERSTART', 'TIMERGET', 'TIMERRESET', 'SCREENCLEAR', 'SCREENWRITE', 'SCREENRENDER', 'DICE', 'ADDITEM', 'HASITEM', 'REMOVEITEM', 'COUNTITEM', 'SETUSERNAME', 'CHATSEND', 'CHATRECEIVE', 'LOBBYADD', 'LOBBYLIST', 'TURNINIT', 'NEXTTURN', 'ISTURN', 'RECONNECT', 'NETINFO', 'NETREADY', 'VERSION', 'HELP'
    ]

    match = difflib.get_close_matches(cmd.upper(), commands, n=1)
    if match:
        return f"Did you mean {match[0]}?"
    return None


# -----------------------------
# TEXT RESOLVER
# -----------------------------
def resolve_text(text):
    out = str(text)

    for var in variables:
        out = out.replace(f"%{var}%", str(variables[var]))

    return out


def eval_path_arg(value):
    raw = strip_inline_comment(str(value).strip())

    if raw == "":
        return ""

    # Quoted paths support variables: WRITEFILE "%name%.txt" "hi"
    if raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
        return str(eval_value(raw))

    # A path can also be stored in a variable: LET file = "save.txt"
    if raw in variables:
        return str(variables[raw])

    # IMPORTANT: unquoted paths are literal filenames.
    # This keeps debug.spy as debug.spy instead of evaluating it to 0.
    return resolve_text(raw)


# -----------------------------
# VALUE EVALUATION
# -----------------------------
def split_outside_quotes(text, sep):
    parts = []
    current = ""
    in_quote = False
    depth = 0
    i = 0

    while i < len(text):
        ch = text[i]

        if ch == '"':
            in_quote = not in_quote
            current += ch
            i += 1
            continue

        if not in_quote:
            if ch in "([{":
                depth += 1
            elif ch in ")]}" and depth > 0:
                depth -= 1

            if ch == sep and depth == 0:
                parts.append(current.strip())
                current = ""
                i += 1
                continue

        current += ch
        i += 1

    parts.append(current.strip())
    return parts


def parse_array_items(content):
    if not content.strip():
        return []

    return [eval_value(item.strip()) for item in split_outside_quotes(content, ",")]




def parse_object_items(content):
    obj = {}

    if not content.strip():
        return obj

    parts = split_outside_quotes(content, ",")

    for part in parts:
        if ":" not in part:
            continue

        key, val = part.split(":", 1)
        key = key.strip().strip('"').strip("'")

        if key == "":
            continue

        obj[key] = eval_value(val.strip())

    return obj


def get_path_value(path):
    parts = str(path).split(".")

    if not parts:
        return ""

    current = variables.get(parts[0], "")

    for key in parts[1:]:
        if isinstance(current, dict):
            current = current.get(key, "")
        else:
            return ""

    return current


def set_path_value(path, value):
    parts = str(path).split(".")

    if len(parts) < 2:
        variables[path] = value
        return

    root = parts[0]

    if root not in variables or not isinstance(variables[root], dict):
        variables[root] = {}

    current = variables[root]

    for key in parts[1:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]

    current[parts[-1]] = value


def has_path_value(path):
    parts = str(path).split(".")

    if not parts or parts[0] not in variables:
        return False

    current = variables.get(parts[0])

    for key in parts[1:]:
        if not isinstance(current, dict) or key not in current:
            return False
        current = current[key]

    return True


def get_array_item(arr_name, index):
    if arr_name in variables and isinstance(variables[arr_name], list):
        try:
            return variables[arr_name][int(index)]
        except:
            return ""
    return ""


def replace_array_refs(expr):
    pattern = r"([a-zA-Z_]\w*)\[(.+?)\]"

    def repl(match):
        arr_name = match.group(1)
        index_expr = match.group(2)
        val = get_array_item(arr_name, eval_value(index_expr))

        if isinstance(val, str):
            try:
                float(val)
                return val
            except:
                return "0"

        return str(val)

    return re.sub(pattern, repl, expr)


def eval_value(value):
    value = strip_inline_comment(str(value).strip())

    if value == "":
        return ""

    low = value.lower()

    # booleans
    if low == "true":
        return True

    if low == "false":
        return False

    # quoted string
    if value.startswith('"') and value.endswith('"') and len(value) >= 2:
        return resolve_text(value[1:-1])

    # %variable%
    if value.startswith("%") and value.endswith("%"):
        return variables.get(value[1:-1], "")

    # arrays
    if value.startswith("[") and value.endswith("]"):
        return parse_array_items(value[1:-1])

    # objects / dictionaries
    if value.startswith("{") and value.endswith("}"):
        return parse_object_items(value[1:-1])

    # object.key / object.deep.key
    if re.match(r"^[a-zA-Z_]\w*(\.[a-zA-Z_]\w*)+$", value):
        return get_path_value(value)

    # string helpers
    if value.startswith("UPPER "):
        return str(eval_value(value[6:].strip())).upper()

    if value.startswith("LOWER "):
        return str(eval_value(value[6:].strip())).lower()

    # length
    if value.startswith("LEN "):
        name = value[4:].strip()

        if name in variables and isinstance(variables[name], list):
            return len(variables[name])

        if name in variables and isinstance(variables[name], str):
            return len(variables[name])

        return 0

    # random
    if value.startswith("RANDOM "):
        parts = value.split()

        if len(parts) == 3:
            low_num = int(eval_value(parts[1]))
            high_num = int(eval_value(parts[2]))
            return random.randint(low_num, high_num)

    # CALL as value: LET result = CALL add 5 10
    if value.startswith("CALL "):
        parts = value[5:].strip().split()
        if len(parts) >= 1:
            name = parts[0]
            args = parts[1:]
            call_function(name, args)
            return variables.get("__return__", "")

    # exact array[index]
    array_match = re.match(r"^([a-zA-Z_]\w*)\[(.+)\]$", value)
    if array_match:
        arr_name = array_match.group(1)
        index = eval_value(array_match.group(2))
        return get_array_item(arr_name, index)

    # direct variable
    if value in variables:
        return variables[value]

    # unknown simple word becomes text, not 0
    if re.match(r"^[a-zA-Z_]\w*$", value):
        return value

    # string concatenation: "Hello " + name
    plus_parts = split_outside_quotes(value, "+")
    if len(plus_parts) > 1 and any(part.startswith('"') or part.endswith('"') for part in plus_parts):
        return "".join(str(eval_value(part)) for part in plus_parts)

    # math fallback
    try:
        math_expr = replace_array_refs(value)
        tokens = tokenize(math_expr)
        rpn = to_rpn(tokens)
        return eval_rpn(rpn)
    except:
        return value


# -----------------------------
# CONDITIONS
# -----------------------------
def eval_condition(condition):
    condition = strip_inline_comment(condition.strip())

    contains_match = re.match(r"^(.+?)\s+CONTAINS\s+(.+)$", condition)
    if contains_match:
        left = str(eval_value(contains_match.group(1).strip()))
        right = str(eval_value(contains_match.group(2).strip()))
        return right in left

    ops = [">=", "<=", "==", "!=", ">", "<"]

    op_funcs = {
        "==": operator.eq,
        "!=": operator.ne,
        ">": operator.gt,
        "<": operator.lt,
        ">=": operator.ge,
        "<=": operator.le,
    }

    for op in ops:
        if op in condition:
            left, right = condition.split(op, 1)
            left_val = eval_value(left.strip())
            right_val = eval_value(right.strip())

            try:
                return op_funcs[op](left_val, right_val)
            except:
                return op_funcs[op](str(left_val), str(right_val))

    return bool(eval_value(condition))


# -----------------------------
# BLOCK PARSER
# -----------------------------
def extract_block(lines, start):
    block = []
    depth = 1
    i = start

    while i < len(lines):
        raw = get_text(lines[i])
        line = strip_inline_comment(raw.strip())

        if line.endswith("{"):
            depth += 1
            block.append(lines[i])
            i += 1
            continue

        if line == "}":
            depth -= 1

            if depth == 0:
                return block, i

            block.append(lines[i])
            i += 1
            continue

        block.append(lines[i])
        i += 1

    print("SpyLang error")
    print("Block was never closed with }")
    return block, i


def skip_empty_lines(lines, i):
    while i < len(lines):
        line = strip_inline_comment(get_text(lines[i]).strip())

        if line == "" or line.startswith("#"):
            i += 1
            continue

        break

    return i


# -----------------------------
# TOKENIZER
# -----------------------------
def tokenize(expr):
    tokens = []
    num = ""
    i = 0

    expr = expr.replace(" ", "")

    while i < len(expr):
        ch = expr[i]

        if ch.isdigit() or ch == ".":
            num += ch
            i += 1
            continue
        else:
            if num:
                tokens.append(num)
                num = ""

        if ch in "+-*/%()":
            tokens.append(ch)
            i += 1
            continue

        var = ""
        while i < len(expr) and (expr[i].isalnum() or expr[i] == "_"):
            var += expr[i]
            i += 1

        if var:
            tokens.append(var)
            continue

        i += 1

    if num:
        tokens.append(num)

    return tokens


# -----------------------------
# RPN CONVERSION
# -----------------------------
def to_rpn(tokens):
    output = []
    ops = []

    for t in tokens:
        if isinstance(t, str) and t.replace(".", "").isdigit():
            output.append(float(t) if "." in t else int(t))

        elif t in precedence:
            while ops and ops[-1] in precedence and precedence[ops[-1]] >= precedence[t]:
                output.append(ops.pop())
            ops.append(t)

        elif t == "(":
            ops.append(t)

        elif t == ")":
            while ops and ops[-1] != "(":
                output.append(ops.pop())
            if ops:
                ops.pop()

        else:
            output.append(variables.get(t, 0))

    while ops:
        output.append(ops.pop())

    return output


# -----------------------------
# RPN EVALUATION
# -----------------------------
def eval_rpn(rpn):
    stack = []

    for t in rpn:
        if isinstance(t, (int, float, bool)):
            stack.append(t)
        else:
            b = stack.pop()
            a = stack.pop()

            if t == "+":
                stack.append(a + b)
            elif t == "-":
                stack.append(a - b)
            elif t == "*":
                stack.append(a * b)
            elif t == "/":
                stack.append(a / b)
            elif t == "%":
                stack.append(a % b)

    if not stack:
        return 0

    return stack[0]


# -----------------------------
# COLOR HELPER
# -----------------------------
def color_text(text, color):
    colors = {
        "RED": "\033[31m",
        "GREEN": "\033[32m",
        "YELLOW": "\033[33m",
        "BLUE": "\033[34m",
        "RESET": "\033[0m"
    }
    return colors.get(color, "") + str(text) + colors["RESET"]


# -----------------------------
# KEY HELPER
# -----------------------------
def read_key():
    # Embedded launcher mode:
    # When SpyLang runs inside the .pyw launcher, stdin is a pipe, not a real console.
    # msvcrt.getch() cannot read from that pipe, so WAITKEY uses one line from the launcher input bar.
    # Type one key in the launcher input bar and press Enter.
    if os.environ.get("SPYLANG_LAUNCHER_CONSOLE") == "1":
        data = sys.stdin.readline()
        if data == "":
            return ""
        return data[0]

    try:
        import msvcrt
        ch = msvcrt.getch()
        try:
            return ch.decode()
        except:
            return ""
    except ImportError:
        import tty
        import termios

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


# -----------------------------
# IP HELPER
# -----------------------------
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return "127.0.0.1"


variables["myip"] = get_local_ip()
variables["netok"] = 0
variables["netmsg"] = 0
variables["netclient"] = -1


# -----------------------------
# NETWORK CONNECTION HELPERS
# -----------------------------
def get_connections():
    conns = []

    for client in net_clients:
        if client is not None:
            conns.append(client)

    if net_conn is not None and net_conn not in conns:
        conns.append(net_conn)

    if net_socket is not None and net_socket not in conns:
        conns.append(net_socket)

    return conns


def get_connection():
    conns = get_connections()
    if conns:
        return conns[0]
    return None


def recv_line_from_socket(conn):
    data = b""

    while not data.endswith(b"\n"):
        chunk = conn.recv(1)

        if not chunk:
            break

        data += chunk

    msg = data.decode(errors="ignore").strip()

    try:
        return int(msg)
    except:
        try:
            return float(msg)
        except:
            return msg


def receive_message(var, timeout=None):
    conns = get_connections()

    if not conns:
        print("RECEIVE error: not connected")
        variables[var] = ""
        variables["netok"] = 0
        variables["netmsg"] = 0
        return

    try:
        if timeout is not None:
            readable, _, _ = select.select(conns, [], [], float(timeout))

            if not readable:
                variables[var] = ""
                variables["netmsg"] = 0
                return

            conn = readable[0]
        else:
            conn = conns[0]

        msg = recv_line_from_socket(conn)
        variables[var] = msg
        variables["netok"] = 1
        variables["netmsg"] = 1

        try:
            variables["netclient"] = net_clients.index(conn)
        except:
            variables["netclient"] = -1

    except Exception as e:
        print("RECEIVE error:", e)
        variables[var] = ""
        variables["netok"] = 0
        variables["netmsg"] = 0




# -----------------------------
# GAME ENGINE HELPERS
# -----------------------------
def game_get_map(map_name):
    if map_name in variables:
        mp = variables[map_name]
    else:
        mp = eval_value(map_name)

    if not isinstance(mp, list):
        return []

    return mp


def game_set_map(map_name, mp):
    if re.match(r"^[a-zA-Z_]\w*$", map_name):
        variables[map_name] = mp


def game_row_to_list(row):
    if isinstance(row, list):
        return [str(x) for x in row]

    return list(str(row))


def game_list_to_row(chars, original_row):
    if isinstance(original_row, list):
        return chars

    return "".join(chars)


def game_height(mp):
    return len(mp)


def game_width(mp):
    if not mp:
        return 0

    return max(len(str(row)) if not isinstance(row, list) else len(row) for row in mp)


def game_get_tile_from_map(mp, x, y):
    try:
        x = int(eval_value(str(x)))
        y = int(eval_value(str(y)))
    except:
        return ""

    if y < 0 or y >= len(mp):
        return ""

    row = game_row_to_list(mp[y])

    if x < 0 or x >= len(row):
        return ""

    return row[x]


def game_set_tile_in_map(mp, x, y, tile):
    try:
        x = int(eval_value(str(x)))
        y = int(eval_value(str(y)))
    except:
        return False

    if y < 0 or y >= len(mp):
        return False

    row_original = mp[y]
    row = game_row_to_list(row_original)

    if x < 0 or x >= len(row):
        return False

    tile = str(tile)
    row[x] = tile[0] if tile else " "
    mp[y] = game_list_to_row(row, row_original)

    return True


# -----------------------------
# V3 MAP / MENU / EVENT HELPERS
# -----------------------------
def split_command_args(text):
    args = []
    current = ""
    in_quote = False
    escaped = False
    depth = 0

    for ch in str(text):
        if ch == "\\" and in_quote:
            escaped = not escaped
            current += ch
            continue
        if ch == '"' and not escaped:
            in_quote = not in_quote
            current += ch
            continue
        escaped = False

        if not in_quote:
            if ch in "[{(":
                depth += 1
            elif ch in "]})" and depth > 0:
                depth -= 1
            if ch.isspace() and depth == 0:
                if current.strip():
                    args.append(current.strip())
                    current = ""
                continue
        current += ch

    if current.strip():
        args.append(current.strip())
    return args


def v3_to_int(value, default=0):
    try:
        return int(eval_value(str(value)))
    except:
        try:
            return int(value)
        except:
            return default


def v3_tile(value):
    tile = str(eval_value(str(value)))
    return tile[0] if tile else " "


def map_normalize(mp):
    if not isinstance(mp, list):
        return []
    return [str("".join(row)) if isinstance(row, list) else str(row) for row in mp]


def map_make(width, height, tile):
    width = max(0, int(width))
    height = max(0, int(height))
    tile = str(tile)[0] if str(tile) else " "
    return [tile * width for _ in range(height)]


def map_copy_value(mp):
    return [str(row) if not isinstance(row, list) else list(row) for row in mp]


def map_draw_line(mp, x1, y1, x2, y2, tile):
    x1 = int(x1); y1 = int(y1); x2 = int(x2); y2 = int(y2)
    dx = abs(x2 - x1)
    dy = -abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx + dy
    x = x1
    y = y1
    while True:
        game_set_tile_in_map(mp, x, y, tile)
        if x == x2 and y == y2:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def menu_store():
    if "__menus__" not in variables or not isinstance(variables.get("__menus__"), dict):
        variables["__menus__"] = {}
    return variables["__menus__"]


def event_store():
    if "__events__" not in variables or not isinstance(variables.get("__events__"), dict):
        variables["__events__"] = {}
    return variables["__events__"]


def event_once_store():
    if "__events_once__" not in variables or not isinstance(variables.get("__events_once__"), dict):
        variables["__events_once__"] = {}
    return variables["__events_once__"]


def render_menu(name):
    menus = menu_store()
    items = menus.get(str(name), [])
    print("==============================")
    print(str(name))
    print("==============================")
    if not items:
        print("(empty menu)")
    else:
        for idx, item in enumerate(items, start=1):
            print(str(idx) + ") " + str(item))


def pick_menu_item(name, choice_text):
    items = menu_store().get(str(name), [])
    if not items:
        return ""
    try:
        idx = int(choice_text) - 1
    except:
        idx = 0
    if idx < 0:
        idx = 0
    if idx >= len(items):
        idx = len(items) - 1
    return items[idx]


def game_find_pos(mp, wanted):
    wanted = str(wanted)

    for y, row_value in enumerate(mp):
        row = game_row_to_list(row_value)

        for x, tile in enumerate(row):
            if str(tile) == wanted:
                return x, y

    return -1, -1


def game_can_move(mp, x, y, blocked="#"):
    tile = game_get_tile_from_map(mp, x, y)

    if tile == "":
        return False

    return str(tile) not in str(blocked)


def game_direction_delta(direction):
    d = str(eval_value(str(direction))).lower()

    if d in ["w", "up", "north", "u"]:
        return 0, -1

    if d in ["s", "down", "south", "dwn"]:
        return 0, 1

    if d in ["a", "left", "west", "l"]:
        return -1, 0

    if d in ["d", "right", "east", "r"]:
        return 1, 0

    return 0, 0


def game_make_screen():
    if "__screen__" not in variables or not isinstance(variables.get("__screen__"), dict):
        variables["__screen__"] = {}

    return variables["__screen__"]


def game_make_timers():
    if "__timers__" not in variables or not isinstance(variables.get("__timers__"), dict):
        variables["__timers__"] = {}

    return variables["__timers__"]


def game_save_dir():
    folder = "saves"

    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)

    return folder


def game_slot_path(slot):
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", str(slot))
    return os.path.join(game_save_dir(), "slot_" + safe + ".json")


def game_json_safe(value):
    try:
        json.dumps(value)
        return value
    except:
        return str(value)


def game_accounts_path():
    return os.path.join(game_save_dir(), "accounts.json")


def game_load_accounts():
    path = game_accounts_path()

    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except:
        return {}


def game_save_accounts(accounts):
    with open(game_accounts_path(), "w", encoding="utf-8") as f:
        json.dump(accounts, f, indent=2)


def quest_store():
    if "__quests__" not in variables or not isinstance(variables.get("__quests__"), dict):
        variables["__quests__"] = {}
    return variables["__quests__"]


def ai_patrol_store():
    if "__ai_patrol__" not in variables or not isinstance(variables.get("__ai_patrol__"), dict):
        variables["__ai_patrol__"] = {}
    return variables["__ai_patrol__"]


def enemy_is_alive(enemy):
    return isinstance(enemy, dict) and float(enemy.get("hp", 0)) > 0


def get_known_commands():
    return set([
        'LET', 'PRINT', 'INPUT', 'IF', 'ELSEIF', 'ELSE', 'WHILE', 'FOR', 'REPEAT', 'FOREACH', 'FUNC', 'CALL', 'RETURN', 'GLOBAL',
        'BREAK', 'EXIT', 'PUSH', 'POP', 'SET', 'DEL', 'CLEAR', 'SAVEVAR', 'LOADVAR', 'WRITEFILE', 'READFILE', 'CLS', 'PAUSE',
        'SLEEP', 'WAITKEY', 'HOST', 'CONNECT', 'SEND', 'RECEIVE', 'TRYRECEIVE', 'BROADCAST', 'PING', 'DISCONNECT', 'IMPORT',
        'AICHOICE', 'AICHANCE', 'AIWEIGHTED', 'AIDECIDE', 'AIREMEMBER', 'AIRECALL', 'AIFORGET', 'AIPATH', 'AISTATE',
        'AIDIALOGUE', 'AINAME', 'AIPERSONALITY', 'AIROUTE', 'AIPRESET', 'AIPATROL', 'AICHASE', 'AIFLEE',
        'DRAWMAP', 'MAPSIZE', 'GETTILE', 'SETTILE', 'FINDPOS', 'CANMOVE', 'MOVEPLAYER', 'DISTANCE', 'MAPTRANS', 'LOADMAP', 'SAVEMAP', 'MAPFILL', 'MAPBORDER', 'MAPRECT', 'MAPLINE', 'MAPCOPY', 'MAPPASTE', 'MAPREPLACE', 'MAPCOUNT', 'MAPFINDALL', 'VIEWPORT', 'MENUCREATE', 'MENUADD', 'MENUCLEAR', 'MENUDRAW', 'MENUCOUNT', 'MENUSHOW', 'SELECTLIST', 'CONFIRM', 'PROMPT', 'EVENTSET', 'EVENTGET', 'EVENTCLEAR', 'EVENTEXISTS', 'EVENTONCE', 'TRIGGER', 'ONTRIGGER',
        'LOADMAP', 'SAVEMAP', 'MAPFILL', 'MAPBORDER', 'MAPRECT', 'MAPLINE', 'MAPCOPY', 'MAPPASTE', 'MAPREPLACE',
        'MAPCOUNT', 'MAPFINDALL', 'VIEWPORT',
        'MENUCREATE', 'MENUADD', 'MENUCLEAR', 'MENUDRAW', 'MENUCOUNT', 'MENUSHOW', 'SELECTLIST', 'CONFIRM', 'PROMPT',
        'EVENTSET', 'EVENTGET', 'EVENTCLEAR', 'EVENTEXISTS', 'EVENTONCE', 'TRIGGER', 'ONTRIGGER',
        'NEWOBJ', 'OBJSET', 'OBJGET', 'OBJHAS', 'OBJDEL', 'OBJKEYS', 'SAVESLOT', 'LOADSLOT', 'DELSLOT', 'LISTSLOTS', 'SLOTMENU',
        'ACCOUNTCREATE', 'ACCOUNTLOGIN', 'ACCOUNTSET', 'ACCOUNTGET', 'ACCOUNTDELETE', 'ACCOUNTLIST',
        'QUESTADD', 'QUESTDONE', 'QUESTSTATUS', 'QUESTLIST', 'XPADD', 'LEVELINFO', 'SHOPBUY', 'SHOPSELL',
        'ENEMYNEW', 'ENEMYHIT', 'ENEMYALIVE', 'ENEMYATTACK', 'ENEMYMOVE',
        'TIMERSTART', 'TIMERGET', 'TIMERRESET', 'SCREENCLEAR', 'SCREENWRITE', 'SCREENRENDER', 'DICE',
        'ADDITEM', 'HASITEM', 'REMOVEITEM', 'COUNTITEM', 'SETUSERNAME', 'GETUSERNAME', 'MAKECHAT', 'CHATSEND', 'CHATRECEIVE',
        'LOBBYADD', 'LOBBYLIST', 'TURNINIT', 'NEXTTURN', 'ISTURN', 'RECONNECT', 'NETINFO', 'NETREADY', 'VERSION', 'HELP'
    ])


def syntax_first_word(stripped):
    if not stripped:
        return ""
    if stripped == "}":
        return "}"
    return stripped.split()[0].upper()


def syntax_check_lines(lines):
    depth = 0
    ok = True
    known = get_known_commands()

    for line_obj in lines:
        raw = get_text(line_obj)
        text = strip_inline_comment(raw)
        stripped = text.strip()

        if stripped == "":
            continue

        in_quote = False
        escaped = False
        for ch in text:
            if ch == "\\" and in_quote:
                escaped = not escaped
                continue
            if ch == '"' and not escaped:
                in_quote = not in_quote
            escaped = False

        if in_quote:
            error(line_obj, "Syntax check: missing closing quote.")
            ok = False

        # Block checks
        if stripped.endswith("{"):
            first = syntax_first_word(stripped)
            if first in ["IF", "ELSEIF", "WHILE", "REPEAT", "FOR", "FOREACH", "FUNC"] or first == "ELSE":
                depth += 1
            else:
                error(line_obj, "Syntax check: this line opens a block, but the command is not a block command.", suggest_command(first))
                ok = False

        if stripped == "}":
            depth -= 1
            if depth < 0:
                error(line_obj, "Syntax check: closing brace without opening brace.")
                ok = False
                depth = 0
            continue

        # Skip lines that are clearly pieces of multi-line arrays/maps/objects.
        if stripped.startswith('"') or stripped.startswith("'") or stripped in ["[", "]", "[", "],", "}", "},"]:
            continue
        if stripped.endswith(",") and (stripped.startswith('"') or stripped.startswith("{") or stripped.startswith("[")):
            continue

        first = syntax_first_word(stripped)
        if first and first not in known:
            error(line_obj, f"Syntax check: unknown command: {first}", suggest_command(first))
            ok = False

        # Simple command-specific header checks
        if first in ["IF", "ELSEIF", "WHILE", "REPEAT", "FOR", "FOREACH", "FUNC"] and not stripped.endswith("{"):
            error(line_obj, f"Syntax check: {first} needs an opening brace {{ at the end.")
            ok = False
        if first == "ELSE" and stripped != "ELSE {":
            error(line_obj, "Syntax check: ELSE must be written as: ELSE {")
            ok = False

    if depth > 0:
        print("SpyLang syntax check failed")
        print("Missing closing brace: }")
        ok = False

    return ok


# -----------------------------
# OFFLINE AI HELPERS
# -----------------------------
AI_NAMES = {
    "spy": ["Agent Shadow", "Silent Viper", "Captain Sneak", "Ghost Falcon", "Lennart Byte", "Agent Midnight", "Cipher Fox"],
    "enemy": ["Goblin Byte", "Captain Bonk", "The Glitch Knight", "Sneaky Bandit", "Dr. Trouble", "Shadow Bot", "The Keyboard Goblin"],
    "robot": ["Unit-404", "ByteBot", "Clank-7", "Circuit Max", "Rusty Prime", "Botrick", "Servo Ghost"],
    "wizard": ["Merlin.exe", "Wandalf", "Professor Spark", "The Lag Mage", "Wizard McBoom", "Arcane Dave"],
    "city": ["Neonburg", "Shadow City", "Bytehaven", "Cipher Town", "Pixelgrad", "Spy Harbor"],
    "weapon": ["The Bonk Stick", "Shadow Blade", "Byte Rifle", "Glitch Dagger", "The Debugger", "Critical Spoon"],
    "quest": ["The Lost Variable", "The Broken Loop", "The Secret Array", "Operation Sandwich", "The Debug Dungeon"]
}

AI_PERSONALITY_LINES = {
    "funny": ["That is hilarious.", "I am not paid enough for this.", "Certified goofy moment.", "My brain just blue-screened."],
    "serious": ["Stay focused.", "This is important.", "Proceed carefully.", "No mistakes."],
    "evil": ["Excellent. Chaos begins.", "You cannot stop me.", "The plan is working.", "Pathetic hero."],
    "coward": ["Please do not hit me.", "I vote we run away.", "That looks dangerous.", "I suddenly remembered an appointment."],
    "heroic": ["For glory!", "I will protect everyone.", "Stand back, I got this.", "Justice does not take breaks."],
    "weird": ["The cheese knows too much.", "I can smell the color purple.", "Do not trust the left shoe.", "My thoughts are shaped like soup."],
    "merchant": ["Best prices in town!", "Buy something shiny.", "No refunds after explosions.", "This item is definitely not cursed."],
    "guard": ["Move along.", "I am watching you.", "No funny business.", "State your purpose."]
}

def ai_percent(value):
    try:
        percent = float(eval_value(str(value)))
    except:
        try:
            percent = float(value)
        except:
            percent = 0
    if percent < 0:
        percent = 0
    if percent > 100:
        percent = 100
    return percent

def ai_parse_weighted(text):
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    items = []
    total = 0.0
    parts = [p.strip() for p in text.split(",") if p.strip() != ""]
    for part in parts:
        if ":" not in part:
            continue
        name, weight = part.split(":", 1)
        name = name.strip().strip('"').strip("'")
        weight = weight.strip()
        try:
            w = float(eval_value(weight))
        except:
            try:
                w = float(weight)
            except:
                w = 0
        if w > 0:
            items.append((name, w))
            total += w
    return items, total

def ai_weighted_choice(weighted_text):
    items, total = ai_parse_weighted(weighted_text)
    if not items or total <= 0:
        return None
    roll = random.uniform(0, total)
    current = 0.0
    for name, weight in items:
        current += weight
        if roll <= current:
            return name
    return items[-1][0]

def ai_simple_decide(hp, target_hp, result_var):
    try:
        hp = float(eval_value(str(hp)))
    except:
        hp = 100
    try:
        target_hp = float(eval_value(str(target_hp)))
    except:
        target_hp = 100

    if hp <= 25:
        variables[result_var] = "Heal"
    elif target_hp <= 25:
        variables[result_var] = "Attack"
    else:
        variables[result_var] = random.choice(["Attack", "Shield", "Charge"])

def ai_make_memory():
    if "__ai_memory__" not in variables or not isinstance(variables.get("__ai_memory__"), dict):
        variables["__ai_memory__"] = {}
    return variables["__ai_memory__"]

def ai_step_towards(ex, ey, px, py):
    try:
        ex = int(eval_value(str(ex)))
        ey = int(eval_value(str(ey)))
        px = int(eval_value(str(px)))
        py = int(eval_value(str(py)))
    except:
        return "none"

    dx = px - ex
    dy = py - ey

    if abs(dx) >= abs(dy):
        if dx > 0:
            return "right"
        if dx < 0:
            return "left"

    if dy > 0:
        return "down"
    if dy < 0:
        return "up"
    return "none"

def ai_route_choice(route_expr):
    route = eval_value(route_expr)
    if isinstance(route, list) and len(route) > 0:
        return random.choice(route)
    return None

# -----------------------------
# FUNCTION CALL HELPER
# -----------------------------
def call_function(name, args):
    if name not in functions:
        print(f"Unknown function: {name}")
        return None

    params, block = functions[name]

    old_vars = variables.copy()

    # remove old return before call
    if "__return__" in variables:
        del variables["__return__"]

    variables["__global_names__"] = []

    for p, a in zip(params, args):
        variables[p] = eval_value(a)

    result = execute(block)

    returned_value = variables.get("__return__", None)
    global_names = variables.get("__global_names__", [])
    global_values = {}

    for g in global_names:
        if g in variables:
            global_values[g] = variables[g]

    variables.clear()
    variables.update(old_vars)

    for g, val in global_values.items():
        variables[g] = val

    if returned_value is not None:
        variables["__return__"] = returned_value

    if result == EXIT_SIGNAL:
        return EXIT_SIGNAL

    return returned_value


# -----------------------------
# EXECUTOR
# -----------------------------
def execute(lines):
    global net_server, net_conn, net_socket, net_clients

    lines = make_lines(lines)
    i = 0

    while i < len(lines):
        raw_line = get_text(lines[i])
        line = strip_inline_comment(raw_line.strip())

        if not line:
            i += 1
            continue

        # ignore closing braces at this level
        if line == "}":
            i += 1
            continue

        # ---------------- BREAK ----------------
        if line == "BREAK":
            return BREAK_SIGNAL

        # ---------------- EXIT ----------------
        if line.startswith("EXIT"):
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                variables["exitcode"] = eval_value(parts[1])
            return EXIT_SIGNAL

        # ---------------- IF / ELSEIF / ELSE ----------------
        if line.startswith("IF "):
            if "{" not in line:
                error(lines[i], "Missing { after IF condition")
                i += 1
                continue

            condition = line[3:].split("{", 1)[0].strip()
            block, new_i = extract_block(lines, i + 1)

            ran = False

            if eval_condition(condition):
                result = execute(block)
                ran = True

                if result == EXIT_SIGNAL:
                    return EXIT_SIGNAL
                if result == RETURN_SIGNAL:
                    return RETURN_SIGNAL
                if result == BREAK_SIGNAL:
                    return BREAK_SIGNAL

            i = skip_empty_lines(lines, new_i + 1)

            # ELSEIF chain, with blank lines allowed
            while i < len(lines) and strip_inline_comment(get_text(lines[i]).strip()).startswith("ELSEIF"):
                elseif_line = strip_inline_comment(get_text(lines[i]).strip())

                if "{" not in elseif_line:
                    error(lines[i], "Missing { after ELSEIF condition")
                    i += 1
                    continue

                condition = elseif_line[7:].split("{", 1)[0].strip()
                block, new_i = extract_block(lines, i + 1)

                if not ran and eval_condition(condition):
                    result = execute(block)
                    ran = True

                    if result == EXIT_SIGNAL:
                        return EXIT_SIGNAL
                    if result == RETURN_SIGNAL:
                        return RETURN_SIGNAL
                    if result == BREAK_SIGNAL:
                        return BREAK_SIGNAL

                i = skip_empty_lines(lines, new_i + 1)

            # ELSE, with blank lines allowed
            if i < len(lines) and strip_inline_comment(get_text(lines[i]).strip()) == "ELSE {":
                block, new_i = extract_block(lines, i + 1)

                if not ran:
                    result = execute(block)

                    if result == EXIT_SIGNAL:
                        return EXIT_SIGNAL
                    if result == RETURN_SIGNAL:
                        return RETURN_SIGNAL
                    if result == BREAK_SIGNAL:
                        return BREAK_SIGNAL

                i = new_i + 1

            continue

        # ---------------- WHILE ----------------
        if line.startswith("WHILE "):
            if "{" not in line:
                error(lines[i], "Missing { after WHILE condition")
                i += 1
                continue

            condition = line[6:].split("{", 1)[0].strip()
            block, new_i = extract_block(lines, i + 1)

            while eval_condition(condition):
                result = execute(block)

                if result == EXIT_SIGNAL:
                    return EXIT_SIGNAL
                if result == RETURN_SIGNAL:
                    return RETURN_SIGNAL
                if result == BREAK_SIGNAL:
                    break

            i = new_i + 1
            continue

        # ---------------- REPEAT ----------------
        if line.startswith("REPEAT "):
            if "{" not in line:
                error(lines[i], "Missing { after REPEAT amount")
                i += 1
                continue

            amount_text = line[7:].split("{", 1)[0].strip()
            amount = int(eval_value(amount_text))
            block, new_i = extract_block(lines, i + 1)

            for _ in range(amount):
                result = execute(block)

                if result == EXIT_SIGNAL:
                    return EXIT_SIGNAL
                if result == RETURN_SIGNAL:
                    return RETURN_SIGNAL
                if result == BREAK_SIGNAL:
                    break

            i = new_i + 1
            continue

        # ---------------- FOR ----------------
        if line.startswith("FOR "):
            if "{" not in line:
                error(lines[i], "Missing { after FOR loop")
                i += 1
                continue

            header = line[4:].split("{", 1)[0].strip()
            match = re.match(r"^([a-zA-Z_]\w*)\s*=\s*(.+?)\s+TO\s+(.+?)(?:\s+STEP\s+(.+))?$", header)

            if not match:
                error(lines[i], "Invalid FOR syntax. Use: FOR i = 1 TO 10 {")
                i += 1
                continue

            var_name = match.group(1)
            start_val = int(eval_value(match.group(2).strip()))
            end_val = int(eval_value(match.group(3).strip()))
            step_val = int(eval_value(match.group(4).strip())) if match.group(4) else 1

            if step_val == 0:
                step_val = 1

            block, new_i = extract_block(lines, i + 1)

            current = start_val
            while (step_val > 0 and current <= end_val) or (step_val < 0 and current >= end_val):
                variables[var_name] = current
                result = execute(block)

                if result == EXIT_SIGNAL:
                    return EXIT_SIGNAL
                if result == RETURN_SIGNAL:
                    return RETURN_SIGNAL
                if result == BREAK_SIGNAL:
                    break

                current += step_val

            i = new_i + 1
            continue

        # ---------------- FOREACH ----------------
        if line.startswith("FOREACH "):
            if "{" not in line:
                error(lines[i], "Missing { after FOREACH")
                i += 1
                continue

            header = line[8:].split("{", 1)[0].strip().split()

            if len(header) != 2:
                error(lines[i], "Invalid FOREACH syntax. Use: FOREACH item inventory {")
                i += 1
                continue

            item_var = header[0]
            arr_name = header[1]
            arr = variables.get(arr_name, [])

            if not isinstance(arr, list):
                arr = []

            block, new_i = extract_block(lines, i + 1)

            for item in arr:
                variables[item_var] = item
                result = execute(block)

                if result == EXIT_SIGNAL:
                    return EXIT_SIGNAL
                if result == RETURN_SIGNAL:
                    return RETURN_SIGNAL
                if result == BREAK_SIGNAL:
                    break

            i = new_i + 1
            continue

        # ---------------- FUNC ----------------
        if line.startswith("FUNC "):
            if "{" not in line:
                error(lines[i], "Missing { after FUNC header")
                i += 1
                continue

            header = line[5:].split("{", 1)[0].strip().split()

            if not header:
                error(lines[i], "Function needs a name")
                i += 1
                continue

            name = header[0]
            params = header[1:]

            block, new_i = extract_block(lines, i + 1)
            functions[name] = (params, block)

            i = new_i + 1
            continue

        # ---------------- GLOBAL ----------------
        if line.startswith("GLOBAL "):
            names = line[7:].replace(",", " ").split()

            if "__global_names__" not in variables:
                variables["__global_names__"] = []

            for name in names:
                if name not in variables["__global_names__"]:
                    variables["__global_names__"].append(name)

            i += 1
            continue

        # ---------------- PUSH ----------------
        if line.startswith("PUSH "):
            parts = line.split(maxsplit=2)

            if len(parts) == 3:
                arr_name = parts[1]
                item = eval_value(parts[2])

                if arr_name not in variables or not isinstance(variables[arr_name], list):
                    variables[arr_name] = []

                variables[arr_name].append(item)

            i += 1
            continue

        # ---------------- POP ----------------
        if line.startswith("POP "):
            arr_name = line[4:].strip()

            if arr_name in variables and isinstance(variables[arr_name], list):
                if len(variables[arr_name]) > 0:
                    variables[arr_name].pop()

            i += 1
            continue

        # ---------------- SET array[index] value / SET object.key value ----------------
        if line.startswith("SET "):
            object_set_match = re.match(r"^SET\s+([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)+)\s+(.+)$", line)

            if object_set_match:
                path = object_set_match.group(1)
                val = eval_value(object_set_match.group(2).strip())
                set_path_value(path, val)

                i += 1
                continue

            set_match = re.match(r"^SET\s+([a-zA-Z_]\w*)\[(.+?)\]\s+(.+)$", line)

            if not set_match:
                error(lines[i], "Invalid SET syntax. Use: SET inventory[0] \"Sword\" OR SET player.hp 80")
                i += 1
                continue

            arr_name = set_match.group(1)
            index = int(eval_value(set_match.group(2).strip()))
            val = eval_value(set_match.group(3).strip())

            if arr_name not in variables or not isinstance(variables[arr_name], list):
                variables[arr_name] = []

            while len(variables[arr_name]) <= index:
                variables[arr_name].append("")

            variables[arr_name][index] = val

            i += 1
            continue

        # ---------------- DEL ----------------
        if line.startswith("DEL "):
            name = line[4:].strip()

            if name in variables:
                del variables[name]

            i += 1
            continue

        # ---------------- CLEAR ----------------
        if line.startswith("CLEAR "):
            name = line[6:].strip()

            if name in variables and isinstance(variables[name], list):
                variables[name] = []

            i += 1
            continue

        # ---------------- CALL ----------------
        if line.startswith("CALL "):
            parts = line[5:].strip().split()

            if len(parts) >= 1:
                name = parts[0]
                args = parts[1:]
                result = call_function(name, args)

                if result == EXIT_SIGNAL:
                    return EXIT_SIGNAL

            i += 1
            continue

        # ---------------- RETURN ----------------
        if line.startswith("RETURN"):
            if line == "RETURN":
                variables["__return__"] = ""
            else:
                variables["__return__"] = eval_value(line[7:].strip())
            return RETURN_SIGNAL

        # ---------------- CLS ----------------
        if line == "CLS":
            # In the GUI launcher stdout is captured through a pipe, so os.system("cls")
            # cannot clear the embedded console. Send a form-feed marker instead;
            # the launcher interprets it as "clear console".
            if os.environ.get("SPYLANG_LAUNCHER_CONSOLE") == "1":
                print("\f", end="", flush=True)
            else:
                os.system("cls" if os.name == "nt" else "clear")
            i += 1
            continue

        # ---------------- PAUSE ----------------
        if line == "PAUSE":
            input("Press Enter to continue...")
            i += 1
            continue

        # ---------------- WAITKEY ----------------
        if line.startswith("WAITKEY"):
            parts = line.split()
            key = read_key()

            if len(parts) == 2:
                variables[parts[1]] = key

            i += 1
            continue

        # ---------------- SLEEP ----------------
        if line.startswith("SLEEP "):
            seconds = eval_value(line[6:].strip())
            time.sleep(float(seconds))
            i += 1
            continue

        # ---------------- SAVEVAR ----------------
        if line.startswith("SAVEVAR "):
            parts = line.split(maxsplit=2)

            if len(parts) != 3:
                error(lines[i], "Usage: SAVEVAR variable file.txt")
                i += 1
                continue

            var_name = parts[1]
            filename = eval_path_arg(parts[2])
            value = variables.get(var_name, "")

            with open(filename, "w", encoding="utf-8") as f:
                json.dump(value, f)

            i += 1
            continue

        # ---------------- LOADVAR ----------------
        if line.startswith("LOADVAR "):
            parts = line.split(maxsplit=2)

            if len(parts) != 3:
                error(lines[i], "Usage: LOADVAR variable file.txt")
                i += 1
                continue

            var_name = parts[1]
            filename = eval_path_arg(parts[2])

            try:
                with open(filename, "r", encoding="utf-8") as f:
                    variables[var_name] = json.load(f)
            except:
                variables[var_name] = ""

            i += 1
            continue

        # ---------------- WRITEFILE ----------------
        if line.startswith("WRITEFILE "):
            parts = line.split(maxsplit=2)

            if len(parts) != 3:
                error(lines[i], "Usage: WRITEFILE file.txt \"text\"")
                i += 1
                continue

            filename = eval_path_arg(parts[1])
            content = str(eval_value(parts[2]))

            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)

            i += 1
            continue

        # ---------------- READFILE ----------------
        if line.startswith("READFILE "):
            parts = line.split(maxsplit=2)

            if len(parts) != 3:
                error(lines[i], "Usage: READFILE file.txt variable")
                i += 1
                continue

            filename = eval_path_arg(parts[1])
            var_name = parts[2]

            try:
                with open(filename, "r", encoding="utf-8") as f:
                    variables[var_name] = f.read()
            except:
                variables[var_name] = ""

            i += 1
            continue

        # ---------------- HOST ----------------
        if line.startswith("HOST "):
            try:
                parts = line.split()
                port = int(eval_value(parts[1]))
                max_clients = int(eval_value(parts[2])) if len(parts) >= 3 else 1

                if max_clients < 1:
                    max_clients = 1

                if net_conn is not None:
                    net_conn.close()
                    net_conn = None

                for client in net_clients:
                    try:
                        client.close()
                    except:
                        pass

                net_clients = []

                if net_server is not None:
                    net_server.close()
                    net_server = None

                net_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                net_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                net_server.bind(("0.0.0.0", port))
                net_server.listen(max_clients)

                print("Hosting on:")
                print(variables.get("myip", "127.0.0.1"))
                print("Port:")
                print(port)
                print("Waiting for connection...")

                for client_num in range(max_clients):
                    conn, addr = net_server.accept()
                    net_clients.append(conn)

                    if net_conn is None:
                        net_conn = conn

                    print("Connected:")
                    print(addr[0])

                variables["netok"] = 1

            except Exception as e:
                print("HOST error:", e)
                variables["netok"] = 0

            i += 1
            continue

        # ---------------- CONNECT ----------------
        if line.startswith("CONNECT "):
            try:
                parts = line.split()

                if len(parts) != 3:
                    print("Usage: CONNECT ip port")
                    variables["netok"] = 0
                    i += 1
                    continue

                ip = str(eval_value(parts[1]))
                port = int(eval_value(parts[2]))

                if net_socket is not None:
                    net_socket.close()
                    net_socket = None

                net_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                net_socket.connect((ip, port))

                print("Connected to host.")
                variables["netok"] = 1

            except Exception as e:
                print("CONNECT error:", e)
                variables["netok"] = 0

            i += 1
            continue

        # ---------------- SEND ----------------
        if line.startswith("SEND "):
            try:
                conn = get_connection()

                if conn is None:
                    print("SEND error: not connected")
                    variables["netok"] = 0
                    i += 1
                    continue

                raw = line[5:].strip()
                message = eval_value(raw)

                conn.sendall((str(message) + "\n").encode())
                variables["netok"] = 1

            except Exception as e:
                print("SEND error:", e)
                variables["netok"] = 0

            i += 1
            continue

        # ---------------- BROADCAST ----------------
        if line.startswith("BROADCAST "):
            try:
                conns = get_connections()

                if not conns:
                    print("BROADCAST error: not connected")
                    variables["netok"] = 0
                    i += 1
                    continue

                message = eval_value(line[10:].strip())

                for conn in conns:
                    conn.sendall((str(message) + "\n").encode())

                variables["netok"] = 1

            except Exception as e:
                print("BROADCAST error:", e)
                variables["netok"] = 0

            i += 1
            continue

        # ---------------- RECEIVE / RECEIVE TIMEOUT ----------------
        if line.startswith("RECEIVE "):
            parts = line.split()

            if len(parts) == 2:
                receive_message(parts[1], None)
            elif len(parts) == 4 and parts[2] == "TIMEOUT":
                receive_message(parts[1], eval_value(parts[3]))
            else:
                print("Usage: RECEIVE msg OR RECEIVE msg TIMEOUT 5")

            i += 1
            continue

        # ---------------- TRYRECEIVE ----------------
        if line.startswith("TRYRECEIVE "):
            parts = line.split()

            if len(parts) == 2:
                receive_message(parts[1], 0)
            else:
                print("Usage: TRYRECEIVE msg")

            i += 1
            continue

        # ---------------- PING ----------------
        if line == "PING":
            conn = get_connection()

            if conn is not None:
                try:
                    variables["netok"] = 1 if conn.fileno() != -1 else 0
                except:
                    variables["netok"] = 0
            else:
                variables["netok"] = 0

            i += 1
            continue

        # ---------------- DISCONNECT ----------------
        if line == "DISCONNECT":
            try:
                if net_conn is not None:
                    net_conn.close()
                    net_conn = None

                if net_socket is not None:
                    net_socket.close()
                    net_socket = None

                for client in net_clients:
                    try:
                        client.close()
                    except:
                        pass

                net_clients = []

                if net_server is not None:
                    net_server.close()
                    net_server = None

                variables["netok"] = 0
                print("Disconnected.")

            except Exception as e:
                print("DISCONNECT error:", e)

            i += 1
            continue

        # ---------------- IMPORT ----------------
        if line.startswith("IMPORT "):
            file = eval_path_arg(line[7:].strip())
            current_file = get_filename(lines[i])
            current_dir = os.path.dirname(os.path.abspath(current_file)) if current_file != "<script>" else os.getcwd()
            path = file

            if not os.path.exists(path):
                path = os.path.join(current_dir, file)

            abs_path = os.path.abspath(path)

            if abs_path not in files_loaded:
                files_loaded.add(abs_path)
                try:
                    with open(abs_path, "r", encoding="utf-8") as f:
                        imported_lines = make_lines(f.readlines(), abs_path)
                        result = execute(imported_lines)
                        if result == EXIT_SIGNAL:
                            return EXIT_SIGNAL
                except Exception as e:
                    print("IMPORT error:", e)

            i += 1
            continue

        # ---------------- LET ----------------
        if line.startswith("LET "):
            if "=" not in line:
                error(lines[i], "Invalid LET syntax. Use: LET name = value")
                i += 1
                continue

            var, value = line[4:].split("=", 1)
            var = var.strip()
            value = value.strip()

            # multi-line array
            if value == "[":
                items = []
                i += 1

                while i < len(lines):
                    part = strip_inline_comment(get_text(lines[i]).strip())

                    if part == "]":
                        break

                    if part.endswith(","):
                        part = part[:-1]

                    items.append(eval_value(part))
                    i += 1

                variables[var] = items
                i += 1
                continue

            variables[var] = eval_value(value)
            i += 1
            continue

        # ---------------- PRINT ----------------
        if line.startswith("PRINT "):
            raw = line[6:]
            parts = raw.split(" ", 1)

            if parts[0] in ["RED", "GREEN", "YELLOW", "BLUE"] and len(parts) > 1:
                text = resolve_text(eval_value(parts[1]))
                print(color_text(text, parts[0]))
            else:
                print(resolve_text(eval_value(raw)))

            i += 1
            continue

        # ---------------- INPUT ----------------
        if line.startswith("INPUT "):
            var = line[6:].strip()
            val = input("> ")

            try:
                val = int(val)
            except:
                try:
                    val = float(val)
                except:
                    pass

            variables[var] = val
            i += 1
            continue


        # ---------------- AICHOICE ----------------
        if line.startswith("AICHOICE "):
            args = line[9:].strip().rsplit(" ", 1)

            if len(args) != 2:
                error(lines[i], "Usage: AICHOICE array variable")
                i += 1
                continue

            source_expr = args[0].strip()
            target_var = args[1].strip()

            if not re.match(r"^[a-zA-Z_]\w*$", target_var):
                error(lines[i], "AICHOICE target must be a variable name. Example: AICHOICE moves enemy_move")
                i += 1
                continue

            if source_expr in variables:
                choices = variables[source_expr]
            else:
                choices = eval_value(source_expr)

            if not isinstance(choices, list):
                error(lines[i], "AICHOICE source must be an array. Example: LET moves = [Attack,Shield,Heal]")
                i += 1
                continue

            if len(choices) == 0:
                error(lines[i], "AICHOICE cannot choose from an empty array.")
                i += 1
                continue

            variables[target_var] = random.choice(choices)
            i += 1
            continue



        # ---------------- AICHANCE ----------------
        if line.startswith("AICHANCE "):
            args = line[9:].strip().rsplit(" ", 1)
            if len(args) != 2:
                error(lines[i], "Usage: AICHANCE percent variable")
                i += 1
                continue

            percent_expr = args[0].strip()
            target_var = args[1].strip()

            if not re.match(r"^[a-zA-Z_]\w*$", target_var):
                error(lines[i], "AICHANCE target must be a variable name. Example: AICHANCE 25 crit")
                i += 1
                continue

            variables[target_var] = random.uniform(0, 100) < ai_percent(percent_expr)
            i += 1
            continue

        # ---------------- AIWEIGHTED ----------------
        if line.startswith("AIWEIGHTED "):
            args = line[11:].strip().rsplit(" ", 1)
            if len(args) != 2:
                error(lines[i], "Usage: AIWEIGHTED [Attack:70,Heal:30] variable")
                i += 1
                continue

            weighted_expr = args[0].strip()
            target_var = args[1].strip()

            if not re.match(r"^[a-zA-Z_]\w*$", target_var):
                error(lines[i], "AIWEIGHTED target must be a variable name. Example: AIWEIGHTED [Attack:70,Heal:30] move")
                i += 1
                continue

            choice = ai_weighted_choice(weighted_expr)
            if choice is None:
                error(lines[i], "AIWEIGHTED needs items with weights. Example: AIWEIGHTED [Attack:70,Shield:20,Heal:10] move")
                i += 1
                continue

            variables[target_var] = choice
            i += 1
            continue

        # ---------------- AIDECIDE ----------------
        if line.startswith("AIDECIDE "):
            args = line[9:].strip().split()
            if len(args) != 3:
                error(lines[i], "Usage: AIDECIDE my_hp target_hp variable")
                i += 1
                continue

            target_var = args[2].strip()
            if not re.match(r"^[a-zA-Z_]\w*$", target_var):
                error(lines[i], "AIDECIDE target must be a variable name. Example: AIDECIDE enemy_hp player_hp move")
                i += 1
                continue

            ai_simple_decide(args[0], args[1], target_var)
            i += 1
            continue

        # ---------------- AIREMEMBER ----------------
        if line.startswith("AIREMEMBER "):
            args = line[11:].strip().split(" ", 1)
            if len(args) != 2:
                error(lines[i], "Usage: AIREMEMBER key value")
                i += 1
                continue

            key = str(eval_value(args[0].strip()))
            value = eval_value(args[1].strip())
            ai_make_memory()[key] = value
            i += 1
            continue

        # ---------------- AIRECALL ----------------
        if line.startswith("AIRECALL "):
            args = line[9:].strip().rsplit(" ", 1)
            if len(args) != 2:
                error(lines[i], "Usage: AIRECALL key variable")
                i += 1
                continue

            key = str(eval_value(args[0].strip()))
            target_var = args[1].strip()

            if not re.match(r"^[a-zA-Z_]\w*$", target_var):
                error(lines[i], "AIRECALL target must be a variable name. Example: AIRECALL player_name result")
                i += 1
                continue

            variables[target_var] = ai_make_memory().get(key, "")
            i += 1
            continue

        # ---------------- AIFORGET ----------------
        if line.startswith("AIFORGET "):
            key = str(eval_value(line[9:].strip()))
            memory = ai_make_memory()
            if key in memory:
                del memory[key]
            i += 1
            continue

        # ---------------- AIPATH ----------------
        if line.startswith("AIPATH "):
            args = line[7:].strip().split()
            if len(args) != 5:
                error(lines[i], "Usage: AIPATH enemy_x enemy_y player_x player_y variable")
                i += 1
                continue

            target_var = args[4].strip()
            if not re.match(r"^[a-zA-Z_]\w*$", target_var):
                error(lines[i], "AIPATH target must be a variable name. Example: AIPATH ex ey px py direction")
                i += 1
                continue

            variables[target_var] = ai_step_towards(args[0], args[1], args[2], args[3])
            i += 1
            continue

        # ---------------- AISTATE ----------------
        if line.startswith("AISTATE "):
            args = line[8:].strip().rsplit(" ", 1)
            if len(args) != 2:
                error(lines[i], "Usage: AISTATE state variable")
                i += 1
                continue

            state = str(eval_value(args[0].strip())).lower()
            target_var = args[1].strip()

            if not re.match(r"^[a-zA-Z_]\w*$", target_var):
                error(lines[i], "AISTATE target must be a variable name. Example: AISTATE chase enemy_state")
                i += 1
                continue

            allowed_states = ["idle", "patrol", "chase", "attack", "flee", "dead"]
            if state not in allowed_states:
                error(lines[i], "Unknown AI state. Use: idle, patrol, chase, attack, flee, dead")
                i += 1
                continue

            variables[target_var] = state
            i += 1
            continue

        # ---------------- AIDIALOGUE ----------------
        if line.startswith("AIDIALOGUE "):
            args = line[11:].strip().rsplit(" ", 1)
            if len(args) != 2:
                error(lines[i], "Usage: AIDIALOGUE array variable")
                i += 1
                continue

            lines_expr = args[0].strip()
            target_var = args[1].strip()

            if not re.match(r"^[a-zA-Z_]\w*$", target_var):
                error(lines[i], "AIDIALOGUE target must be a variable name. Example: AIDIALOGUE lines npc_line")
                i += 1
                continue

            dialogue_lines = eval_value(lines_expr)
            if not isinstance(dialogue_lines, list) and lines_expr in variables:
                dialogue_lines = variables[lines_expr]

            if not isinstance(dialogue_lines, list) or len(dialogue_lines) == 0:
                error(lines[i], "AIDIALOGUE needs a non-empty array. Example: LET lines = [Hello,Go away]")
                i += 1
                continue

            variables[target_var] = random.choice(dialogue_lines)
            i += 1
            continue

        # ---------------- AINAME ----------------
        if line.startswith("AINAME "):
            args = line[7:].strip().rsplit(" ", 1)
            if len(args) != 2:
                error(lines[i], "Usage: AINAME type variable")
                i += 1
                continue

            name_type = str(eval_value(args[0].strip())).lower()
            target_var = args[1].strip()

            if not re.match(r"^[a-zA-Z_]\w*$", target_var):
                error(lines[i], "AINAME target must be a variable name. Example: AINAME spy npc_name")
                i += 1
                continue

            if name_type not in AI_NAMES:
                name_type = "spy"

            variables[target_var] = random.choice(AI_NAMES[name_type])
            i += 1
            continue

        # ---------------- AIPERSONALITY ----------------
        if line.startswith("AIPERSONALITY "):
            args = line[14:].strip().rsplit(" ", 1)
            if len(args) != 2:
                error(lines[i], "Usage: AIPERSONALITY personality variable")
                i += 1
                continue

            personality = str(eval_value(args[0].strip())).lower()
            target_var = args[1].strip()

            if not re.match(r"^[a-zA-Z_]\w*$", target_var):
                error(lines[i], "AIPERSONALITY target must be a variable name. Example: AIPERSONALITY funny line")
                i += 1
                continue

            if personality not in AI_PERSONALITY_LINES:
                error(lines[i], "Unknown personality. Use: funny, serious, evil, coward, heroic, weird, merchant, guard")
                i += 1
                continue

            variables[target_var] = random.choice(AI_PERSONALITY_LINES[personality])
            i += 1
            continue

        # ---------------- AIROUTE ----------------
        if line.startswith("AIROUTE "):
            args = line[8:].strip().rsplit(" ", 1)
            if len(args) != 2:
                error(lines[i], "Usage: AIROUTE array variable")
                i += 1
                continue

            route_expr = args[0].strip()
            target_var = args[1].strip()

            if not re.match(r"^[a-zA-Z_]\w*$", target_var):
                error(lines[i], "AIROUTE target must be a variable name. Example: AIROUTE [left,right,forward] path")
                i += 1
                continue

            path = ai_route_choice(route_expr)
            if path is None:
                error(lines[i], "AIROUTE needs a non-empty array. Example: AIROUTE [left,right,forward] path")
                i += 1
                continue

            variables[target_var] = path
            i += 1
            continue




        # ---------------- V3 LOADMAP ----------------
        if line.startswith("LOADMAP "):
            args = split_command_args(line[8:].strip())
            if len(args) != 2:
                error(lines[i], "Usage: LOADMAP file.txt map_var")
                i += 1
                continue
            filename = eval_path_arg(args[0])
            target = args[1]
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    variables[target] = [row.rstrip("\n") for row in f.readlines()]
            except Exception as e:
                variables[target] = []
                error(lines[i], "LOADMAP failed: " + str(e))
            i += 1
            continue

        # ---------------- V3 SAVEMAP ----------------
        if line.startswith("SAVEMAP "):
            args = split_command_args(line[8:].strip())
            if len(args) != 2:
                error(lines[i], "Usage: SAVEMAP map file.txt")
                i += 1
                continue
            mp = map_normalize(game_get_map(args[0]))
            filename = eval_path_arg(args[1])
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write("\n".join(mp))
            except Exception as e:
                error(lines[i], "SAVEMAP failed: " + str(e))
            i += 1
            continue

        # ---------------- V3 MAPFILL ----------------
        if line.startswith("MAPFILL "):
            args = split_command_args(line[8:].strip())
            if len(args) != 4:
                error(lines[i], "Usage: MAPFILL width height tile map_var")
                i += 1
                continue
            variables[args[3]] = map_make(v3_to_int(args[0]), v3_to_int(args[1]), v3_tile(args[2]))
            i += 1
            continue

        # ---------------- V3 MAPBORDER ----------------
        if line.startswith("MAPBORDER "):
            args = split_command_args(line[10:].strip())
            if len(args) != 2:
                error(lines[i], "Usage: MAPBORDER map tile")
                i += 1
                continue
            map_name = args[0]
            mp = game_get_map(map_name)
            tile = v3_tile(args[1])
            h = game_height(mp)
            w = game_width(mp)
            if h > 0 and w > 0:
                for x in range(w):
                    game_set_tile_in_map(mp, x, 0, tile)
                    game_set_tile_in_map(mp, x, h - 1, tile)
                for y in range(h):
                    game_set_tile_in_map(mp, 0, y, tile)
                    game_set_tile_in_map(mp, w - 1, y, tile)
            game_set_map(map_name, mp)
            i += 1
            continue

        # ---------------- V3 MAPRECT ----------------
        if line.startswith("MAPRECT "):
            args = split_command_args(line[8:].strip())
            if len(args) != 6:
                error(lines[i], "Usage: MAPRECT map x y width height tile")
                i += 1
                continue
            map_name = args[0]
            mp = game_get_map(map_name)
            x0 = v3_to_int(args[1]); y0 = v3_to_int(args[2])
            w = v3_to_int(args[3]); h = v3_to_int(args[4])
            tile = v3_tile(args[5])
            for yy in range(y0, y0 + h):
                for xx in range(x0, x0 + w):
                    game_set_tile_in_map(mp, xx, yy, tile)
            game_set_map(map_name, mp)
            i += 1
            continue

        # ---------------- V3 MAPLINE ----------------
        if line.startswith("MAPLINE "):
            args = split_command_args(line[8:].strip())
            if len(args) != 6:
                error(lines[i], "Usage: MAPLINE map x1 y1 x2 y2 tile")
                i += 1
                continue
            map_name = args[0]
            mp = game_get_map(map_name)
            map_draw_line(mp, v3_to_int(args[1]), v3_to_int(args[2]), v3_to_int(args[3]), v3_to_int(args[4]), v3_tile(args[5]))
            game_set_map(map_name, mp)
            i += 1
            continue

        # ---------------- V3 MAPCOPY ----------------
        if line.startswith("MAPCOPY "):
            args = split_command_args(line[8:].strip())
            if len(args) != 2:
                error(lines[i], "Usage: MAPCOPY source_map target_map")
                i += 1
                continue
            variables[args[1]] = map_copy_value(game_get_map(args[0]))
            i += 1
            continue

        # ---------------- V3 MAPPASTE ----------------
        if line.startswith("MAPPASTE "):
            args = split_command_args(line[9:].strip())
            if len(args) != 4:
                error(lines[i], "Usage: MAPPASTE target_map source_map x y")
                i += 1
                continue
            target_name = args[0]
            target = game_get_map(target_name)
            source = game_get_map(args[1])
            x0 = v3_to_int(args[2]); y0 = v3_to_int(args[3])
            for yy, row_value in enumerate(source):
                row = game_row_to_list(row_value)
                for xx, tile in enumerate(row):
                    game_set_tile_in_map(target, x0 + xx, y0 + yy, tile)
            game_set_map(target_name, target)
            i += 1
            continue

        # ---------------- V3 MAPREPLACE ----------------
        if line.startswith("MAPREPLACE "):
            args = split_command_args(line[11:].strip())
            if len(args) != 3:
                error(lines[i], "Usage: MAPREPLACE map old_tile new_tile")
                i += 1
                continue
            map_name = args[0]
            mp = game_get_map(map_name)
            old = v3_tile(args[1]); new = v3_tile(args[2])
            for y in range(game_height(mp)):
                row = game_row_to_list(mp[y])
                for x, tile in enumerate(row):
                    if str(tile) == old:
                        row[x] = new
                mp[y] = game_list_to_row(row, mp[y])
            game_set_map(map_name, mp)
            i += 1
            continue

        # ---------------- V3 MAPCOUNT ----------------
        if line.startswith("MAPCOUNT "):
            args = split_command_args(line[9:].strip())
            if len(args) != 3:
                error(lines[i], "Usage: MAPCOUNT map tile count_var")
                i += 1
                continue
            mp = game_get_map(args[0])
            wanted = v3_tile(args[1])
            count = 0
            for row_value in mp:
                for tile in game_row_to_list(row_value):
                    if str(tile) == wanted:
                        count += 1
            variables[args[2]] = count
            i += 1
            continue

        # ---------------- V3 MAPFINDALL ----------------
        if line.startswith("MAPFINDALL "):
            args = split_command_args(line[11:].strip())
            if len(args) != 3:
                error(lines[i], "Usage: MAPFINDALL map tile positions_var")
                i += 1
                continue
            mp = game_get_map(args[0])
            wanted = v3_tile(args[1])
            positions = []
            for y, row_value in enumerate(mp):
                for x, tile in enumerate(game_row_to_list(row_value)):
                    if str(tile) == wanted:
                        positions.append({"x": x, "y": y})
            variables[args[2]] = positions
            i += 1
            continue

        # ---------------- V3 VIEWPORT ----------------
        if line.startswith("VIEWPORT "):
            args = split_command_args(line[9:].strip())
            if len(args) != 6:
                error(lines[i], "Usage: VIEWPORT map x y width height view_var")
                i += 1
                continue
            mp = map_normalize(game_get_map(args[0]))
            x0 = v3_to_int(args[1]); y0 = v3_to_int(args[2])
            w = v3_to_int(args[3]); h = v3_to_int(args[4])
            view = []
            for yy in range(y0, y0 + h):
                row = ""
                for xx in range(x0, x0 + w):
                    row += game_get_tile_from_map(mp, xx, yy) or " "
                view.append(row)
            variables[args[5]] = view
            i += 1
            continue

        # ---------------- V3 MENUCREATE ----------------
        if line.startswith("MENUCREATE "):
            name = str(eval_value(line[11:].strip()))
            menu_store()[name] = []
            i += 1
            continue

        # ---------------- V3 MENUADD ----------------
        if line.startswith("MENUADD "):
            args = split_command_args(line[8:].strip())
            if len(args) != 2:
                error(lines[i], "Usage: MENUADD menu item")
                i += 1
                continue
            name = str(eval_value(args[0]))
            item = eval_value(args[1])
            menus = menu_store()
            if name not in menus:
                menus[name] = []
            menus[name].append(item)
            i += 1
            continue

        # ---------------- V3 MENUCLEAR ----------------
        if line.startswith("MENUCLEAR "):
            name = str(eval_value(line[10:].strip()))
            menu_store()[name] = []
            i += 1
            continue

        # ---------------- V3 MENUDRAW ----------------
        if line.startswith("MENUDRAW "):
            name = str(eval_value(line[9:].strip()))
            render_menu(name)
            i += 1
            continue

        # ---------------- V3 MENUCOUNT ----------------
        if line.startswith("MENUCOUNT "):
            args = split_command_args(line[10:].strip())
            if len(args) != 2:
                error(lines[i], "Usage: MENUCOUNT menu count_var")
                i += 1
                continue
            name = str(eval_value(args[0]))
            variables[args[1]] = len(menu_store().get(name, []))
            i += 1
            continue

        # ---------------- V3 MENUSHOW ----------------
        if line.startswith("MENUSHOW "):
            args = split_command_args(line[9:].strip())
            if len(args) not in [2, 4]:
                error(lines[i], "Usage: MENUSHOW menu choice_var OR MENUSHOW menu choice_var DEFAULT number")
                i += 1
                continue
            name = str(eval_value(args[0]))
            target = args[1]
            render_menu(name)
            if len(args) == 4 and args[2].upper() == "DEFAULT":
                choice_text = str(eval_value(args[3]))
            else:
                choice_text = input("Choose: ").strip()
            variables[target] = pick_menu_item(name, choice_text)
            i += 1
            continue

        # ---------------- V3 SELECTLIST ----------------
        if line.startswith("SELECTLIST "):
            args = split_command_args(line[11:].strip())
            if len(args) not in [2, 4]:
                error(lines[i], "Usage: SELECTLIST array choice_var OR SELECTLIST array choice_var DEFAULT number")
                i += 1
                continue
            arr = eval_value(args[0])
            if not isinstance(arr, list):
                arr = variables.get(args[0], [])
            if not isinstance(arr, list):
                arr = []
            for idx, item in enumerate(arr, start=1):
                print(str(idx) + ") " + str(item))
            if len(args) == 4 and args[2].upper() == "DEFAULT":
                choice_text = str(eval_value(args[3]))
            else:
                choice_text = input("Choose: ").strip()
            try:
                idx = int(choice_text) - 1
            except:
                idx = 0
            if idx < 0: idx = 0
            if idx >= len(arr): idx = len(arr) - 1
            variables[args[1]] = arr[idx] if arr else ""
            i += 1
            continue

        # ---------------- V3 CONFIRM ----------------
        if line.startswith("CONFIRM "):
            args = split_command_args(line[8:].strip())
            if len(args) not in [2, 4]:
                error(lines[i], "Usage: CONFIRM message result_var OR CONFIRM message result_var DEFAULT yes")
                i += 1
                continue
            message = str(eval_value(args[0]))
            target = args[1]
            if len(args) == 4 and args[2].upper() == "DEFAULT":
                answer = str(eval_value(args[3])).lower()
            else:
                answer = input(message + " (y/n): ").strip().lower()
            variables[target] = answer in ["y", "yes", "true", "1"]
            i += 1
            continue

        # ---------------- V3 PROMPT ----------------
        if line.startswith("PROMPT "):
            args = split_command_args(line[7:].strip())
            if len(args) not in [2, 4]:
                error(lines[i], "Usage: PROMPT message result_var OR PROMPT message result_var DEFAULT value")
                i += 1
                continue
            message = str(eval_value(args[0]))
            target = args[1]
            if len(args) == 4 and args[2].upper() == "DEFAULT":
                variables[target] = eval_value(args[3])
            else:
                variables[target] = input(message + ": ")
            i += 1
            continue

        # ---------------- V3 EVENTSET ----------------
        if line.startswith("EVENTSET "):
            args = split_command_args(line[9:].strip())
            if len(args) != 2:
                error(lines[i], "Usage: EVENTSET name value")
                i += 1
                continue
            event_store()[str(eval_value(args[0]))] = eval_value(args[1])
            i += 1
            continue

        # ---------------- V3 EVENTGET ----------------
        if line.startswith("EVENTGET "):
            args = split_command_args(line[9:].strip())
            if len(args) != 2:
                error(lines[i], "Usage: EVENTGET name result_var")
                i += 1
                continue
            variables[args[1]] = event_store().get(str(eval_value(args[0])), False)
            i += 1
            continue

        # ---------------- V3 EVENTCLEAR ----------------
        if line.startswith("EVENTCLEAR "):
            name = str(eval_value(line[11:].strip()))
            event_store().pop(name, None)
            event_once_store().pop(name, None)
            i += 1
            continue

        # ---------------- V3 EVENTEXISTS ----------------
        if line.startswith("EVENTEXISTS "):
            args = split_command_args(line[12:].strip())
            if len(args) != 2:
                error(lines[i], "Usage: EVENTEXISTS name result_var")
                i += 1
                continue
            variables[args[1]] = str(eval_value(args[0])) in event_store()
            i += 1
            continue

        # ---------------- V3 EVENTONCE ----------------
        if line.startswith("EVENTONCE "):
            args = split_command_args(line[10:].strip())
            if len(args) != 2:
                error(lines[i], "Usage: EVENTONCE name result_var")
                i += 1
                continue
            name = str(eval_value(args[0]))
            once = event_once_store()
            if once.get(name, False):
                variables[args[1]] = False
            else:
                once[name] = True
                variables[args[1]] = True
            i += 1
            continue

        # ---------------- V3 TRIGGER ----------------
        if line.startswith("TRIGGER "):
            name = str(eval_value(line[8:].strip()))
            event_store()[name] = True
            i += 1
            continue

        # ---------------- V3 ONTRIGGER ----------------
        if line.startswith("ONTRIGGER "):
            args = split_command_args(line[10:].strip())
            if len(args) != 2:
                error(lines[i], "Usage: ONTRIGGER name function")
                i += 1
                continue
            name = str(eval_value(args[0]))
            func = args[1]
            if event_store().get(name, False):
                result = call_function(func, [])
                if result == EXIT_SIGNAL:
                    return EXIT_SIGNAL
            i += 1
            continue

        # ---------------- DRAWMAP ----------------
        if line.startswith("DRAWMAP "):
            mp = game_get_map(line[8:].strip())

            for row in mp:
                if isinstance(row, list):
                    print("".join(str(x) for x in row))
                else:
                    print(str(row))

            i += 1
            continue

        # ---------------- MAPSIZE ----------------
        if line.startswith("MAPSIZE "):
            args = line[8:].strip().split()

            if len(args) != 3:
                error(lines[i], "Usage: MAPSIZE map width_var height_var")
                i += 1
                continue

            mp = game_get_map(args[0])
            variables[args[1]] = game_width(mp)
            variables[args[2]] = game_height(mp)

            i += 1
            continue

        # ---------------- GETTILE ----------------
        if line.startswith("GETTILE "):
            args = line[8:].strip().split()

            if len(args) != 4:
                error(lines[i], "Usage: GETTILE map x y variable")
                i += 1
                continue

            mp = game_get_map(args[0])
            variables[args[3]] = game_get_tile_from_map(mp, args[1], args[2])

            i += 1
            continue

        # ---------------- SETTILE ----------------
        if line.startswith("SETTILE "):
            args = line[8:].strip().split(maxsplit=3)

            if len(args) != 4:
                error(lines[i], "Usage: SETTILE map x y tile")
                i += 1
                continue

            map_name = args[0]
            mp = game_get_map(map_name)
            tile = eval_value(args[3])
            game_set_tile_in_map(mp, args[1], args[2], tile)
            game_set_map(map_name, mp)

            i += 1
            continue

        # ---------------- FINDPOS ----------------
        if line.startswith("FINDPOS "):
            args = line[8:].strip().split()

            if len(args) != 4:
                error(lines[i], "Usage: FINDPOS map tile x_var y_var")
                i += 1
                continue

            mp = game_get_map(args[0])
            wanted = eval_value(args[1])
            x, y = game_find_pos(mp, wanted)
            variables[args[2]] = x
            variables[args[3]] = y

            i += 1
            continue

        # ---------------- CANMOVE ----------------
        if line.startswith("CANMOVE "):
            args = line[8:].strip().split()

            if len(args) not in [4, 5]:
                error(lines[i], "Usage: CANMOVE map x y variable OR CANMOVE map x y variable walls")
                i += 1
                continue

            mp = game_get_map(args[0])
            blocked = eval_value(args[4]) if len(args) == 5 else "#"
            variables[args[3]] = game_can_move(mp, args[1], args[2], blocked)

            i += 1
            continue

        # ---------------- MOVEPLAYER ----------------
        if line.startswith("MOVEPLAYER "):
            args = line[11:].strip().split()

            if len(args) not in [5, 7]:
                error(lines[i], "Usage: MOVEPLAYER map x_var y_var direction moved_var OR MOVEPLAYER map x_var y_var direction moved_var player_tile empty_tile")
                i += 1
                continue

            map_name = args[0]
            x_var = args[1]
            y_var = args[2]
            direction = args[3]
            moved_var = args[4]
            player_tile = eval_value(args[5]) if len(args) == 7 else "P"
            empty_tile = eval_value(args[6]) if len(args) == 7 else "."

            mp = game_get_map(map_name)
            x = int(eval_value(x_var))
            y = int(eval_value(y_var))
            dx, dy = game_direction_delta(direction)
            nx = x + dx
            ny = y + dy

            if game_can_move(mp, nx, ny):
                game_set_tile_in_map(mp, x, y, empty_tile)
                game_set_tile_in_map(mp, nx, ny, player_tile)
                game_set_map(map_name, mp)
                variables[x_var] = nx
                variables[y_var] = ny
                variables[moved_var] = True
            else:
                variables[moved_var] = False

            i += 1
            continue

        # ---------------- DISTANCE ----------------
        if line.startswith("DISTANCE "):
            args = line[9:].strip().split()

            if len(args) != 5:
                error(lines[i], "Usage: DISTANCE x1 y1 x2 y2 variable")
                i += 1
                continue

            x1 = int(eval_value(args[0]))
            y1 = int(eval_value(args[1]))
            x2 = int(eval_value(args[2]))
            y2 = int(eval_value(args[3]))
            variables[args[4]] = abs(x1 - x2) + abs(y1 - y2)

            i += 1
            continue

        # ---------------- NEWOBJ ----------------
        if line.startswith("NEWOBJ "):
            name = line[7:].strip()

            if not re.match(r"^[a-zA-Z_]\w*$", name):
                error(lines[i], "Usage: NEWOBJ variable")
                i += 1
                continue

            variables[name] = {}
            i += 1
            continue

        # ---------------- OBJSET ----------------
        if line.startswith("OBJSET "):
            args = line[7:].strip().split(maxsplit=2)

            if len(args) != 3:
                error(lines[i], "Usage: OBJSET object key value")
                i += 1
                continue

            obj_name = args[0]
            key = str(eval_value(args[1]))
            val = eval_value(args[2])

            if obj_name not in variables or not isinstance(variables[obj_name], dict):
                variables[obj_name] = {}

            variables[obj_name][key] = val
            i += 1
            continue

        # ---------------- OBJGET ----------------
        if line.startswith("OBJGET "):
            args = line[7:].strip().split()

            if len(args) != 3:
                error(lines[i], "Usage: OBJGET object key variable")
                i += 1
                continue

            obj = variables.get(args[0], {})
            key = str(eval_value(args[1]))
            variables[args[2]] = obj.get(key, "") if isinstance(obj, dict) else ""

            i += 1
            continue

        # ---------------- OBJHAS ----------------
        if line.startswith("OBJHAS "):
            args = line[7:].strip().split()

            if len(args) != 3:
                error(lines[i], "Usage: OBJHAS object key variable")
                i += 1
                continue

            obj = variables.get(args[0], {})
            key = str(eval_value(args[1]))
            variables[args[2]] = key in obj if isinstance(obj, dict) else False

            i += 1
            continue

        # ---------------- OBJDEL ----------------
        if line.startswith("OBJDEL "):
            args = line[7:].strip().split()

            if len(args) != 2:
                error(lines[i], "Usage: OBJDEL object key")
                i += 1
                continue

            obj = variables.get(args[0], {})
            key = str(eval_value(args[1]))

            if isinstance(obj, dict) and key in obj:
                del obj[key]

            i += 1
            continue

        # ---------------- OBJKEYS ----------------
        if line.startswith("OBJKEYS "):
            args = line[8:].strip().split()

            if len(args) != 2:
                error(lines[i], "Usage: OBJKEYS object variable")
                i += 1
                continue

            obj = variables.get(args[0], {})
            variables[args[1]] = list(obj.keys()) if isinstance(obj, dict) else []

            i += 1
            continue

        # ---------------- SAVESLOT ----------------
        if line.startswith("SAVESLOT "):
            args = line[9:].strip().split()

            if len(args) != 2:
                error(lines[i], "Usage: SAVESLOT slot variable")
                i += 1
                continue

            slot = eval_value(args[0])
            var_name = args[1]
            value = game_json_safe(variables.get(var_name, ""))

            with open(game_slot_path(slot), "w", encoding="utf-8") as f:
                json.dump(value, f, indent=2)

            i += 1
            continue

        # ---------------- LOADSLOT ----------------
        if line.startswith("LOADSLOT "):
            args = line[9:].strip().split()

            if len(args) != 2:
                error(lines[i], "Usage: LOADSLOT slot variable")
                i += 1
                continue

            slot = eval_value(args[0])
            path = game_slot_path(slot)

            try:
                with open(path, "r", encoding="utf-8") as f:
                    variables[args[1]] = json.load(f)
            except:
                variables[args[1]] = ""

            i += 1
            continue

        # ---------------- DELSLOT ----------------
        if line.startswith("DELSLOT "):
            slot = eval_value(line[8:].strip())
            path = game_slot_path(slot)

            if os.path.exists(path):
                os.remove(path)

            i += 1
            continue

        # ---------------- LISTSLOTS ----------------
        if line.startswith("LISTSLOTS "):
            target = line[10:].strip()
            folder = game_save_dir()
            slots = []

            for filename in os.listdir(folder):
                if filename.startswith("slot_") and filename.endswith(".json"):
                    slots.append(filename[5:-5])

            variables[target] = slots
            i += 1
            continue

        # ---------------- TIMERSTART ----------------
        if line.startswith("TIMERSTART "):
            name = str(eval_value(line[11:].strip()))
            game_make_timers()[name] = time.time()
            i += 1
            continue

        # ---------------- TIMERGET ----------------
        if line.startswith("TIMERGET "):
            args = line[9:].strip().split()

            if len(args) != 2:
                error(lines[i], "Usage: TIMERGET timer variable")
                i += 1
                continue

            name = str(eval_value(args[0]))
            timers = game_make_timers()

            if name in timers:
                variables[args[1]] = round(time.time() - timers[name], 3)
            else:
                variables[args[1]] = 0

            i += 1
            continue

        # ---------------- TIMERRESET ----------------
        if line.startswith("TIMERRESET "):
            name = str(eval_value(line[11:].strip()))
            game_make_timers()[name] = time.time()
            i += 1
            continue

        # ---------------- SCREENCLEAR ----------------
        if line == "SCREENCLEAR":
            variables["__screen__"] = {}
            i += 1
            continue

        # ---------------- SCREENWRITE ----------------
        if line.startswith("SCREENWRITE "):
            args = line[12:].strip().split(maxsplit=2)

            if len(args) != 3:
                error(lines[i], "Usage: SCREENWRITE x y text")
                i += 1
                continue

            x = int(eval_value(args[0]))
            y = int(eval_value(args[1]))
            text = str(eval_value(args[2]))
            game_make_screen()[(x, y)] = text

            i += 1
            continue

        # ---------------- SCREENRENDER ----------------
        if line == "SCREENRENDER":
            screen = game_make_screen()

            if not screen:
                i += 1
                continue

            max_y = max(pos[1] for pos in screen)
            max_x = max(pos[0] + len(str(text)) for pos, text in screen.items())

            for y in range(max_y + 1):
                row = [" "] * max_x

                for (x, sy), text in screen.items():
                    if sy != y:
                        continue

                    text = str(text)
                    for idx, ch in enumerate(text):
                        if 0 <= x + idx < len(row):
                            row[x + idx] = ch

                print("".join(row).rstrip())

            i += 1
            continue

        # ---------------- DICE ----------------
        if line.startswith("DICE "):
            args = line[5:].strip().split()

            if len(args) != 3:
                error(lines[i], "Usage: DICE count sides variable")
                i += 1
                continue

            count = int(eval_value(args[0]))
            sides = int(eval_value(args[1]))
            target = args[2]

            if count < 1:
                count = 1
            if sides < 1:
                sides = 1

            rolls = [random.randint(1, sides) for _ in range(count)]
            variables[target] = sum(rolls)
            variables[target + "_rolls"] = rolls

            i += 1
            continue

        # ---------------- ADDITEM ----------------
        if line.startswith("ADDITEM "):
            args = line[8:].strip().split(maxsplit=1)

            if len(args) != 2:
                error(lines[i], "Usage: ADDITEM inventory item")
                i += 1
                continue

            arr_name = args[0]
            item = eval_value(args[1])

            if arr_name not in variables or not isinstance(variables[arr_name], list):
                variables[arr_name] = []

            variables[arr_name].append(item)

            i += 1
            continue

        # ---------------- HASITEM ----------------
        if line.startswith("HASITEM "):
            args = line[8:].strip().split(maxsplit=2)

            if len(args) != 3:
                error(lines[i], "Usage: HASITEM inventory item variable")
                i += 1
                continue

            arr = variables.get(args[0], [])
            item = eval_value(args[1])
            variables[args[2]] = item in arr if isinstance(arr, list) else False

            i += 1
            continue

        # ---------------- REMOVEITEM ----------------
        if line.startswith("REMOVEITEM "):
            args = line[11:].strip().split(maxsplit=2)

            if len(args) != 3:
                error(lines[i], "Usage: REMOVEITEM inventory item variable")
                i += 1
                continue

            arr_name = args[0]
            item = eval_value(args[1])
            removed_var = args[2]
            arr = variables.get(arr_name, [])

            if isinstance(arr, list) and item in arr:
                arr.remove(item)
                variables[removed_var] = True
            else:
                variables[removed_var] = False

            i += 1
            continue

        # ---------------- COUNTITEM ----------------
        if line.startswith("COUNTITEM "):
            args = line[10:].strip().split(maxsplit=2)

            if len(args) != 3:
                error(lines[i], "Usage: COUNTITEM inventory item variable")
                i += 1
                continue

            arr = variables.get(args[0], [])
            item = eval_value(args[1])
            variables[args[2]] = arr.count(item) if isinstance(arr, list) else 0

            i += 1
            continue



        # ---------------- v2.5 AI PRESET ----------------
        if line.startswith("AIPRESET "):
            args = line[9:].strip().split()
            if len(args) != 2:
                error(lines[i], "Usage: AIPRESET aggressive move_var")
                i += 1
                continue
            preset = str(eval_value(args[0])).lower()
            target = args[1]
            presets = {
                "aggressive": "[Attack:75,HeavyAttack:15,Shield:5,Heal:5]",
                "defensive": "[Attack:35,Shield:40,Heal:20,Charge:5]",
                "coward": "[Flee:45,Shield:30,Heal:20,Attack:5]",
                "boss": "[Attack:45,HeavyAttack:30,Shield:10,Heal:10,Taunt:5]",
                "chaotic": "[Attack:20,HeavyAttack:20,Shield:20,Heal:20,Taunt:20]"
            }
            variables[target] = ai_weighted_choice(presets.get(preset, presets["chaotic"]))
            i += 1
            continue

        # ---------------- AIPATROL ----------------
        if line.startswith("AIPATROL "):
            args = line[9:].strip().split()
            if len(args) != 3:
                error(lines[i], "Usage: AIPATROL route id direction_var")
                i += 1
                continue
            route = eval_value(args[0])
            patrol_id = str(eval_value(args[1]))
            target = args[2]
            if not isinstance(route, list) or len(route) == 0:
                error(lines[i], "AIPATROL route must be a non-empty array.")
                i += 1
                continue
            store = ai_patrol_store()
            idx = int(store.get(patrol_id, 0))
            variables[target] = route[idx % len(route)]
            store[patrol_id] = (idx + 1) % len(route)
            i += 1
            continue

        # ---------------- AICHASE ----------------
        if line.startswith("AICHASE "):
            args = line[8:].strip().split()
            if len(args) != 5:
                error(lines[i], "Usage: AICHASE enemy_x enemy_y player_x player_y direction_var")
                i += 1
                continue
            variables[args[4]] = ai_step_towards(args[0], args[1], args[2], args[3])
            i += 1
            continue

        # ---------------- AIFLEE ----------------
        if line.startswith("AIFLEE "):
            args = line[7:].strip().split()
            if len(args) != 5:
                error(lines[i], "Usage: AIFLEE enemy_x enemy_y player_x player_y direction_var")
                i += 1
                continue
            d = ai_step_towards(args[0], args[1], args[2], args[3])
            opposite = {"left":"right", "right":"left", "up":"down", "down":"up", "none":"none"}
            variables[args[4]] = opposite.get(d, "none")
            i += 1
            continue

        # ---------------- MAPTRANS ----------------
        if line.startswith("MAPTRANS "):
            args = line[9:].strip().split()
            if len(args) != 10:
                error(lines[i], "Usage: MAPTRANS x y trigger_x trigger_y target_map target_x target_y map_var x_var y_var")
                i += 1
                continue
            x = int(eval_value(args[0])); y = int(eval_value(args[1]))
            tx = int(eval_value(args[2])); ty = int(eval_value(args[3]))
            if x == tx and y == ty:
                variables[args[7]] = eval_value(args[4])
                variables[args[8]] = int(eval_value(args[5]))
                variables[args[9]] = int(eval_value(args[6]))
                variables["mapchanged"] = True
            else:
                variables["mapchanged"] = False
            i += 1
            continue

        # ---------------- SLOTMENU ----------------
        if line.startswith("SLOTMENU "):
            target = line[9:].strip()
            folder = game_save_dir()
            slots = []
            for filename in os.listdir(folder):
                if filename.startswith("slot_") and filename.endswith(".json"):
                    slots.append(filename[5:-5])
            slots.sort()
            variables[target] = slots
            print("Save slots:")
            if len(slots) == 0:
                print("No save slots found.")
            else:
                for s in slots:
                    print(s)
            i += 1
            continue

        # ---------------- ACCOUNTCREATE ----------------
        if line.startswith("ACCOUNTCREATE "):
            args = line[14:].strip().split()
            if len(args) != 3:
                error(lines[i], "Usage: ACCOUNTCREATE username password ok_var")
                i += 1
                continue
            username = str(eval_value(args[0])); password = str(eval_value(args[1])); ok_var = args[2]
            accounts = game_load_accounts()
            if username in accounts:
                variables[ok_var] = False
            else:
                accounts[username] = {"password": password, "data": {}}
                game_save_accounts(accounts)
                variables[ok_var] = True
            i += 1
            continue

        # ---------------- ACCOUNTLOGIN ----------------
        if line.startswith("ACCOUNTLOGIN "):
            args = line[13:].strip().split()
            if len(args) != 3:
                error(lines[i], "Usage: ACCOUNTLOGIN username password ok_var")
                i += 1
                continue
            username = str(eval_value(args[0])); password = str(eval_value(args[1])); ok_var = args[2]
            accounts = game_load_accounts()
            variables[ok_var] = username in accounts and accounts[username].get("password") == password
            if variables[ok_var]:
                variables["current_account"] = username
            i += 1
            continue

        # ---------------- ACCOUNTSET ----------------
        if line.startswith("ACCOUNTSET "):
            args = line[11:].strip().split(maxsplit=2)
            if len(args) != 3:
                error(lines[i], "Usage: ACCOUNTSET username key value")
                i += 1
                continue
            username = str(eval_value(args[0])); key = str(eval_value(args[1])); val = eval_value(args[2])
            accounts = game_load_accounts()
            if username not in accounts:
                accounts[username] = {"password": "", "data": {}}
            accounts[username].setdefault("data", {})[key] = val
            game_save_accounts(accounts)
            i += 1
            continue

        # ---------------- ACCOUNTGET ----------------
        if line.startswith("ACCOUNTGET "):
            args = line[11:].strip().split()
            if len(args) != 3:
                error(lines[i], "Usage: ACCOUNTGET username key variable")
                i += 1
                continue
            username = str(eval_value(args[0])); key = str(eval_value(args[1])); target = args[2]
            accounts = game_load_accounts()
            variables[target] = accounts.get(username, {}).get("data", {}).get(key, "")
            i += 1
            continue

        # ---------------- ACCOUNTDELETE ----------------
        if line.startswith("ACCOUNTDELETE "):
            args = line[14:].strip().split()
            if len(args) != 2:
                error(lines[i], "Usage: ACCOUNTDELETE username ok_var")
                i += 1
                continue
            username = str(eval_value(args[0])); ok_var = args[1]
            accounts = game_load_accounts()
            if username in accounts:
                del accounts[username]
                game_save_accounts(accounts)
                variables[ok_var] = True
            else:
                variables[ok_var] = False
            i += 1
            continue

        # ---------------- ACCOUNTLIST ----------------
        if line.startswith("ACCOUNTLIST "):
            target = line[12:].strip()
            variables[target] = sorted(list(game_load_accounts().keys()))
            i += 1
            continue

        # ---------------- QUESTADD ----------------
        if line.startswith("QUESTADD "):
            args = line[9:].strip().split(maxsplit=1)
            if len(args) != 2:
                error(lines[i], "Usage: QUESTADD id title")
                i += 1
                continue
            qid = str(eval_value(args[0])); title = str(eval_value(args[1]))
            quest_store()[qid] = {"title": title, "done": False}
            i += 1
            continue

        # ---------------- QUESTDONE ----------------
        if line.startswith("QUESTDONE "):
            qid = str(eval_value(line[10:].strip()))
            quests = quest_store()
            if qid in quests:
                quests[qid]["done"] = True
            i += 1
            continue

        # ---------------- QUESTSTATUS ----------------
        if line.startswith("QUESTSTATUS "):
            args = line[12:].strip().split()
            if len(args) != 2:
                error(lines[i], "Usage: QUESTSTATUS id variable")
                i += 1
                continue
            qid = str(eval_value(args[0])); target = args[1]
            variables[target] = quest_store().get(qid, {}).get("done", False)
            i += 1
            continue

        # ---------------- QUESTLIST ----------------
        if line.startswith("QUESTLIST "):
            target = line[10:].strip()
            out = []
            for qid, q in quest_store().items():
                out.append(qid + ":" + q.get("title", "") + ":" + ("done" if q.get("done") else "open"))
            variables[target] = out
            i += 1
            continue

        # ---------------- XPADD ----------------
        if line.startswith("XPADD "):
            args = line[6:].strip().split()
            if len(args) != 4:
                error(lines[i], "Usage: XPADD xp_var level_var amount leveled_var")
                i += 1
                continue
            xp_var, level_var, amount_expr, leveled_var = args
            xp = int(eval_value(xp_var)) if xp_var in variables else 0
            level = int(eval_value(level_var)) if level_var in variables else 1
            xp += int(eval_value(amount_expr))
            leveled = False
            while xp >= level * 100:
                xp -= level * 100
                level += 1
                leveled = True
            variables[xp_var] = xp
            variables[level_var] = level
            variables[leveled_var] = leveled
            i += 1
            continue

        # ---------------- LEVELINFO ----------------
        if line.startswith("LEVELINFO "):
            args = line[10:].strip().split()
            if len(args) != 3:
                error(lines[i], "Usage: LEVELINFO xp_var level_var needed_var")
                i += 1
                continue
            xp = int(eval_value(args[0])) if args[0] in variables else 0
            level = int(eval_value(args[1])) if args[1] in variables else 1
            variables[args[2]] = max(0, level * 100 - xp)
            i += 1
            continue

        # ---------------- SHOPBUY ----------------
        if line.startswith("SHOPBUY "):
            args = line[8:].strip().split(maxsplit=4)
            if len(args) != 5:
                error(lines[i], "Usage: SHOPBUY gold_var cost item inventory ok_var")
                i += 1
                continue
            gold_var, cost_expr, item_expr, inv_name, ok_var = args
            gold = int(eval_value(gold_var))
            cost = int(eval_value(cost_expr))
            if gold >= cost:
                if "." in gold_var:
                    set_path_value(gold_var, gold - cost)
                else:
                    variables[gold_var] = gold - cost
                if inv_name not in variables or not isinstance(variables[inv_name], list):
                    variables[inv_name] = []
                variables[inv_name].append(eval_value(item_expr))
                variables[ok_var] = True
            else:
                variables[ok_var] = False
            i += 1
            continue

        # ---------------- SHOPSELL ----------------
        if line.startswith("SHOPSELL "):
            args = line[9:].strip().split(maxsplit=4)
            if len(args) != 5:
                error(lines[i], "Usage: SHOPSELL inventory item price gold_var ok_var")
                i += 1
                continue
            inv_name, item_expr, price_expr, gold_var, ok_var = args
            item = eval_value(item_expr); price = int(eval_value(price_expr)); inv = variables.get(inv_name, [])
            if isinstance(inv, list) and item in inv:
                inv.remove(item)
                new_gold = int(eval_value(gold_var)) + price
                if "." in gold_var:
                    set_path_value(gold_var, new_gold)
                else:
                    variables[gold_var] = new_gold
                variables[ok_var] = True
            else:
                variables[ok_var] = False
            i += 1
            continue

        # ---------------- ENEMYNEW ----------------
        if line.startswith("ENEMYNEW "):
            args = line[9:].strip().split()
            if len(args) != 6:
                error(lines[i], "Usage: ENEMYNEW name hp damage x y variable")
                i += 1
                continue
            variables[args[5]] = {"name": str(eval_value(args[0])), "hp": int(eval_value(args[1])), "damage": int(eval_value(args[2])), "x": int(eval_value(args[3])), "y": int(eval_value(args[4])), "state": "idle"}
            i += 1
            continue

        # ---------------- ENEMYHIT ----------------
        if line.startswith("ENEMYHIT "):
            args = line[9:].strip().split()
            if len(args) != 3:
                error(lines[i], "Usage: ENEMYHIT enemy damage dead_var")
                i += 1
                continue
            enemy = variables.get(args[0], {})
            if isinstance(enemy, dict):
                enemy["hp"] = int(enemy.get("hp", 0)) - int(eval_value(args[1]))
                variables[args[2]] = enemy["hp"] <= 0
            else:
                variables[args[2]] = True
            i += 1
            continue

        # ---------------- ENEMYALIVE ----------------
        if line.startswith("ENEMYALIVE "):
            args = line[11:].strip().split()
            if len(args) != 2:
                error(lines[i], "Usage: ENEMYALIVE enemy variable")
                i += 1
                continue
            variables[args[1]] = enemy_is_alive(variables.get(args[0], {}))
            i += 1
            continue

        # ---------------- ENEMYATTACK ----------------
        if line.startswith("ENEMYATTACK "):
            args = line[12:].strip().split()
            if len(args) != 3:
                error(lines[i], "Usage: ENEMYATTACK enemy hp_var damage_var")
                i += 1
                continue
            enemy = variables.get(args[0], {})
            dmg = int(enemy.get("damage", 0)) if isinstance(enemy, dict) else 0
            current_hp = int(eval_value(args[1]))
            if "." in args[1]:
                set_path_value(args[1], current_hp - dmg)
            else:
                variables[args[1]] = current_hp - dmg
            variables[args[2]] = dmg
            i += 1
            continue

        # ---------------- ENEMYMOVE ----------------
        if line.startswith("ENEMYMOVE "):
            args = line[10:].strip().split()
            if len(args) != 4:
                error(lines[i], "Usage: ENEMYMOVE enemy map direction moved_var")
                i += 1
                continue
            enemy = variables.get(args[0], {})
            mp = game_get_map(args[1])
            if isinstance(enemy, dict):
                dx, dy = game_direction_delta(args[2])
                nx = int(enemy.get("x", 0)) + dx; ny = int(enemy.get("y", 0)) + dy
                if game_can_move(mp, nx, ny):
                    enemy["x"] = nx; enemy["y"] = ny; variables[args[3]] = True
                else:
                    variables[args[3]] = False
            else:
                variables[args[3]] = False
            i += 1
            continue

        # ---------------- Multiplayer helpers ----------------
        if line.startswith("SETUSERNAME "):
            variables["username"] = str(eval_value(line[12:].strip()))
            i += 1
            continue

        if line.startswith("CHATSEND "):
            name = str(variables.get("username", "Player"))
            msg = name + ": " + str(eval_value(line[9:].strip()))
            conns = get_connections()
            for conn in conns:
                try:
                    conn.sendall((msg + "\n").encode())
                except:
                    pass
            i += 1
            continue

        if line.startswith("CHATRECEIVE "):
            receive_message(line[12:].strip(), timeout=0.1)
            i += 1
            continue

        if line.startswith("LOBBYADD "):
            if "lobby_players" not in variables or not isinstance(variables.get("lobby_players"), list):
                variables["lobby_players"] = []
            name = str(eval_value(line[9:].strip()))
            if name not in variables["lobby_players"]:
                variables["lobby_players"].append(name)
            i += 1
            continue

        if line.startswith("LOBBYLIST "):
            variables[line[10:].strip()] = variables.get("lobby_players", [])
            i += 1
            continue

        if line.startswith("TURNINIT "):
            args = line[9:].strip().split()
            if len(args) != 2:
                error(lines[i], "Usage: TURNINIT players_array current_var")
                i += 1
                continue
            players = eval_value(args[0])
            variables["__turn_players__"] = players if isinstance(players, list) else []
            variables["__turn_index__"] = 0
            variables[args[1]] = variables["__turn_players__"][0] if variables["__turn_players__"] else ""
            i += 1
            continue

        if line.startswith("NEXTTURN "):
            target = line[9:].strip()
            players = variables.get("__turn_players__", [])
            if players:
                variables["__turn_index__"] = (int(variables.get("__turn_index__", 0)) + 1) % len(players)
                variables[target] = players[variables["__turn_index__"]]
            else:
                variables[target] = ""
            i += 1
            continue

        if line.startswith("ISTURN "):
            args = line[7:].strip().split()
            if len(args) != 2:
                error(lines[i], "Usage: ISTURN player result_var")
                i += 1
                continue
            current_players = variables.get("__turn_players__", [])
            idx = int(variables.get("__turn_index__", 0))
            current = current_players[idx] if current_players else ""
            variables[args[1]] = str(eval_value(args[0])) == str(current)
            i += 1
            continue

        if line.startswith("RECONNECT "):
            args = line[10:].strip().split()
            if len(args) != 3:
                error(lines[i], "Usage: RECONNECT ip port ok_var")
                i += 1
                continue
            try:
                if net_socket:
                    net_socket.close()
            except:
                pass
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((str(eval_value(args[0])), int(eval_value(args[1]))))
                net_socket = s
                variables[args[2]] = True
                variables["netok"] = 1
            except:
                variables[args[2]] = False
                variables["netok"] = 0
            i += 1
            continue

        if line == "NETINFO":
            print("Local IP:")
            print(variables.get("myip", ""))
            print("netok:")
            print(variables.get("netok", 0))
            print("Connected sockets:")
            print(len(get_connections()))
            i += 1
            continue

        if line.startswith("NETREADY "):
            variables[line[9:].strip()] = len(get_connections()) > 0
            i += 1
            continue


        # ---------------- VERSION ----------------
        if line == "VERSION":
            print("SpyLang " + SPYLANG_VERSION)
            i += 1
            continue

        # ---------------- HELP ----------------
        if line.startswith("HELP"):
            print('SpyLang commands: LET, PRINT, INPUT, IF, ELSEIF, ELSE, WHILE, FOR, REPEAT, FOREACH, FUNC, CALL, RETURN, GLOBAL, BREAK, EXIT, PUSH, POP, SET, DEL, CLEAR, SAVEVAR, LOADVAR, WRITEFILE, READFILE, CLS, PAUSE, SLEEP, WAITKEY, HOST, CONNECT, SEND, RECEIVE, TRYRECEIVE, BROADCAST, PING, DISCONNECT, IMPORT, AICHOICE, AICHANCE, AIWEIGHTED, AIDECIDE, AIREMEMBER, AIRECALL, AIFORGET, AIPATH, AISTATE, AIDIALOGUE, AINAME, AIPERSONALITY, AIROUTE, DRAWMAP, MAPSIZE, GETTILE, SETTILE, FINDPOS, CANMOVE, MOVEPLAYER, DISTANCE, LOADMAP, SAVEMAP, MAPFILL, MAPBORDER, MAPRECT, MAPLINE, MAPCOPY, MAPPASTE, MAPREPLACE, MAPCOUNT, MAPFINDALL, VIEWPORT, MENUCREATE, MENUADD, MENUCLEAR, MENUDRAW, MENUCOUNT, MENUSHOW, SELECTLIST, CONFIRM, PROMPT, EVENTSET, EVENTGET, EVENTCLEAR, EVENTEXISTS, EVENTONCE, TRIGGER, ONTRIGGER, NEWOBJ, OBJSET, OBJGET, OBJHAS, OBJDEL, OBJKEYS, SAVESLOT, LOADSLOT, DELSLOT, LISTSLOTS, TIMERSTART, TIMERGET, TIMERRESET, SCREENCLEAR, SCREENWRITE, SCREENRENDER, DICE, ADDITEM, HASITEM, REMOVEITEM, COUNTITEM, VERSION, HELP')
            i += 1
            continue

        first_word = line.split()[0] if line.split() else line
        error(lines[i], f"Unknown command: {line}", suggest_command(first_word))
        i += 1

    return None


# -----------------------------
# RUN FILE
# -----------------------------
def run_file(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            lines = make_lines(f.readlines(), filename)

        if not syntax_check_lines(lines):
            return

        execute(lines)

    except SystemExit:
        raise

    except KeyboardInterrupt:
        print("SpyLang stopped by user.")

    except Exception as e:
        print("SpyLang crash recovered")
        print("Error:", e)
        if os.environ.get("SPYLANG_DEBUG", "0") == "1":
            traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python spy.py file.spy")
    else:
        run_file(sys.argv[1])
