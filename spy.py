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

SPYLANG_VERSION = "v1.5-prerelease1"


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
    print(message)
    if suggestion:
        print(suggestion)


def suggest_command(cmd):
    commands = [
        "LET", "PRINT", "INPUT", "IF", "ELSEIF", "ELSE", "WHILE", "FOR", "REPEAT",
        "FOREACH", "FUNC", "CALL", "RETURN", "GLOBAL", "BREAK", "EXIT", "PUSH", "POP",
        "SET", "DEL", "CLEAR", "SAVEVAR", "LOADVAR", "WRITEFILE", "READFILE", "CLS",
        "PAUSE", "SLEEP", "WAITKEY", "HOST", "CONNECT", "SEND", "RECEIVE", "TRYRECEIVE",
        "BROADCAST", "PING", "DISCONNECT", "IMPORT", "VERSION", "HELP"
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
            if ch in "([":
                depth += 1
            elif ch in ")]" and depth > 0:
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

        # ---------------- SET array[index] value ----------------
        if line.startswith("SET "):
            set_match = re.match(r"^SET\s+([a-zA-Z_]\w*)\[(.+?)\]\s+(.+)$", line)

            if not set_match:
                error(lines[i], "Invalid SET syntax. Use: SET inventory[0] \"Sword\"")
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

        # ---------------- VERSION ----------------
        if line == "VERSION":
            print("SpyLang " + SPYLANG_VERSION)
            i += 1
            continue

        # ---------------- HELP ----------------
        if line.startswith("HELP"):
            print("SpyLang commands: LET, PRINT, INPUT, IF, ELSEIF, ELSE, WHILE, FOR, REPEAT, FOREACH, FUNC, CALL, RETURN, GLOBAL, BREAK, EXIT, PUSH, POP, SET, DEL, CLEAR, SAVEVAR, LOADVAR, WRITEFILE, READFILE, HOST, CONNECT, SEND, RECEIVE, TRYRECEIVE, BROADCAST, PING, DISCONNECT, IMPORT")
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
    with open(filename, "r", encoding="utf-8") as f:
        execute(make_lines(f.readlines(), filename))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python spy.py file.spy")
    else:
        run_file(sys.argv[1])
