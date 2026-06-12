import sys
import operator
import os
import time
import random
import re
import socket

variables = {}
functions = {}
files_loaded = set()

net_server = None
net_conn = None
net_socket = None

RETURN_SIGNAL = "__RETURN__"
BREAK_SIGNAL = "__BREAK__"


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
# VALUE EVALUATION
# -----------------------------
def eval_value(value):
    value = str(value).strip()

    if value.startswith("[") and value.endswith("]"):
        content = value[1:-1]

        if not content.strip():
            return []

        return [item.strip() for item in content.split(",")]

    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]

    if value.startswith("%") and value.endswith("%"):
        return variables.get(value[1:-1], "")

    array_match = re.match(r"^([a-zA-Z_]\w*)\[(.+)\]$", value)
    if array_match:
        arr_name = array_match.group(1)
        index = eval_value(array_match.group(2))

        if arr_name in variables and isinstance(variables[arr_name], list):
            try:
                item = variables[arr_name][index]
                try:
                    return int(item)

                except:
                    try:
                        return float(item)

                    except:
                        return item
            except:
                return ""
        return ""

    if value in variables:
        return variables[value]

    if value.startswith("LEN "):
        name = value[4:].strip()

        if name in variables and isinstance(variables[name], list):
            return len(variables[name])

        return 0

    if value.startswith("RANDOM "):
        parts = value.split()

        if len(parts) == 3:
            low = int(eval_value(parts[1]))
            high = int(eval_value(parts[2]))

            return random.randint(low, high)

    try:
        tokens = tokenize(value)
        rpn = to_rpn(tokens)
        return eval_rpn(rpn)
    except:
        return value


# -----------------------------
# BLOCK PARSER
# -----------------------------
def extract_block(lines, start):
    block = []
    depth = 1
    i = start

    while i < len(lines):
        line = lines[i].strip()

        if line.endswith("{"):
            depth += 1
            block.append(line)
            i += 1
            continue

        if line == "}":
            depth -= 1

            if depth == 0:
                return block, i

            # keep nested closing braces
            block.append(line)
            i += 1
            continue

        block.append(line)
        i += 1

    return block, i

# -----------------------------
# TEXT RESOLVER
# -----------------------------
def resolve_text(text):
    out = str(text)

    for var in variables:
        out = out.replace(f"%{var}%", str(variables[var]))

    return out


# -----------------------------
# TOKENIZER
# -----------------------------
def tokenize(expr):
    tokens = []
    num = ""
    var = ""
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
        if isinstance(t, str) and (t.replace(".", "").isdigit()):
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
        if isinstance(t, (int, float)):
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

# -----------------------------
# NETWORK CONNECTION HELPER
# -----------------------------
def get_connection():
    if net_conn is not None:
        return net_conn

    if net_socket is not None:
        return net_socket

    return None

# -----------------------------
# EXECUTOR
# -----------------------------
def execute(lines):
    global net_server, net_conn, net_socket
    i = 0

    ops = {
        "==": operator.eq,
        "!=": operator.ne,
        ">": operator.gt,
        "<": operator.lt,
        ">=": operator.ge,
        "<=": operator.le,
    }

    while i < len(lines):
        line = lines[i].strip()

        if not line or line.startswith("#"):
            i += 1
            continue

        # ---------------- BREAK ----------------
        if line == "BREAK":

            return BREAK_SIGNAL

        # ---------------- IF / ELSEIF / ELSE ----------------
        if line.startswith("IF "):

            condition = line[3:].split("{")[0].strip()
            left, op, right = condition.split()

            block, new_i = extract_block(lines, i + 1)

            ran = False

            if op in ops and ops[op](eval_value(left), eval_value(right)):
                result = execute(block)
                ran = True

                if result == RETURN_SIGNAL:
                    return RETURN_SIGNAL
                if result == BREAK_SIGNAL:
                    return BREAK_SIGNAL


            i = new_i + 1


            # ELSEIF chain
            while i < len(lines) and lines[i].strip().startswith("ELSEIF"):

                elseif_line = lines[i].strip()

                condition = elseif_line[7:].split("{")[0].strip()
                left, op, right = condition.split()

                block, new_i = extract_block(lines, i + 1)

                if not ran:
                    if op in ops and ops[op](eval_value(left), eval_value(right)):
                        result = execute(block)
                        ran = True

                        if result == RETURN_SIGNAL:
                            return RETURN_SIGNAL
                        if result == BREAK_SIGNAL:
                            return BREAK_SIGNAL


                i = new_i + 1


            # ELSE
            if i < len(lines) and lines[i].strip() == "ELSE {":

                block, new_i = extract_block(lines, i + 1)

                if not ran:
                    result = execute(block)

                    if result == RETURN_SIGNAL:
                        return RETURN_SIGNAL
                    if result == BREAK_SIGNAL:
                        return BREAK_SIGNAL

                i = new_i + 1


            continue

        # ---------------- WHILE ----------------
        if line.startswith("WHILE "):
            condition = line[6:].split("{")[0].strip()
            parts = condition.split()

            if len(parts) != 3:
                i += 1
                continue

            left, op, right = parts

            if op not in ops:
                i += 1
                continue

            block, new_i = extract_block(lines, i + 1)

            while True:
                if not ops[op](eval_value(left), eval_value(right)):
                    break

                result = execute(block)

                if result == RETURN_SIGNAL:
                    return RETURN_SIGNAL
                if result == BREAK_SIGNAL:
                    break

            i = new_i + 1
            continue


        # ---------------- FUNC ----------------
        if line.startswith("FUNC "):
            header = line[5:].split("{")[0].strip().split()
            name = header[0]
            params = header[1:]

            block, new_i = extract_block(lines, i + 1)
            functions[name] = (params, block)

            i = new_i + 1
            continue

        # ---------------- PUSH ----------------
        if line.startswith("PUSH "):
            parts = line.split(maxsplit=2)

            if len(parts) == 3:
                arr_name = parts[1]
                item = eval_value(parts[2])

                if arr_name in variables and isinstance(variables[arr_name], list):
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

        # ---------------- CALL ----------------
        if line.startswith("CALL "):
            parts = line[5:].strip().split()
            name = parts[0]
            args = parts[1:]

            if name in functions:
                params, block = functions[name]

                old_vars = variables.copy()

                for p, a in zip(params, args):
                    variables[p] = eval_value(a)

                result = execute(block)

                returned_value = variables.get("__return__", None)

                variables.clear()
                variables.update(old_vars)

                if returned_value is not None:
                    variables["__return__"] = returned_value

            i += 1
            continue

        # ---------------- RETURN ----------------
        if line.startswith("RETURN "):
            variables["__return__"] = eval_value(line[7:].strip())
            return None

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


        # ---------------- SLEEP ----------------
        if line.startswith("SLEEP "):
            seconds = eval_value(line[6:].strip())
            time.sleep(float(seconds))
            i += 1
            continue

        # ---------------- HOST ----------------
        if line.startswith("HOST "):
            try:
                port = int(eval_value(line[5:].strip()))

                if net_conn is not None:
                    net_conn.close()
                    net_conn = None

                if net_server is not None:
                    net_server.close()
                    net_server = None

                net_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                net_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                net_server.bind(("0.0.0.0", port))
                net_server.listen(1)

                print("Hosting on:")
                print(variables.get("myip", "127.0.0.1"))
                print("Port:")
                print(port)
                print("Waiting for connection...")

                net_conn, addr = net_server.accept()

                print("Connected:")
                print(addr[0])

            except Exception as e:
                print("HOST error:", e)

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

                variables["netok"] = 1
                print("Connected to host.")

            except Exception as e:
                variables["netok"] = 0
                print("CONNECT error:", e)

            i += 1
            continue

        # ---------------- SEND ----------------
        if line.startswith("SEND "):
            try:
                conn = get_connection()

                if conn is None:
                    print("SEND error: not connected")
                    i += 1
                    continue

                raw = line[5:].strip()
                message = eval_value(raw)

                conn.sendall((str(message) + "\n").encode())

            except Exception as e:
                print("SEND error:", e)

            i += 1
            continue


        # ---------------- RECEIVE ----------------
        if line.startswith("RECEIVE "):
            try:
                conn = get_connection()

                if conn is None:
                    print("RECEIVE error: not connected")
                    i += 1
                    continue

                var = line[8:].strip()

                data = b""

                while not data.endswith(b"\n"):
                    chunk = conn.recv(1)

                    if not chunk:
                        break

                    data += chunk

                msg = data.decode().strip()

                try:
                    msg = int(msg)
                except:
                    try:
                        msg = float(msg)
                    except:
                        pass

                variables[var] = msg

            except Exception as e:
                print("RECEIVE error:", e)

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

                if net_server is not None:
                    net_server.close()
                    net_server = None

                print("Disconnected.")

            except Exception as e:
                print("DISCONNECT error:", e)

            i += 1
            continue

        # ---------------- IMPORT ----------------
        if line.startswith("IMPORT "):
            file = line[7:].strip()

            if file not in files_loaded:
                files_loaded.add(file)
                with open(file, "r") as f:
                    execute(f.readlines())

            i += 1
            continue


        # ---------------- LET ----------------
        if line.startswith("LET "):

            var, value = line[4:].split("=",1)

            value = value.strip()


            # multi-line array
            if value == "[":

                items = []
                i += 1

                while i < len(lines):

                    part = lines[i].strip()

                    if part == "]":
                        break

                    items.append(part.strip(","))

                    i += 1

                variables[var.strip()] = items

                i += 1
                continue


            variables[var.strip()] = eval_value(value)

            i += 1
            continue

        # ---------------- PRINT ----------------
        if line.startswith("PRINT "):
            raw = line[6:]

            parts = raw.split(" ", 1)

            if parts[0] in ["RED", "GREEN", "YELLOW", "BLUE"] and len(parts) > 1:
                text = eval_value(parts[1])
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


        print(f"Unknown command: {line}")
        i += 1


# -----------------------------
# RUN FILE
# -----------------------------
def run_file(filename):
    with open(filename, "r") as f:
        execute(f.readlines())


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python spy.py file.spy")
    else:
        run_file(sys.argv[1])