import sys
import operator
import os
import time

variables = {}
functions = {}
files_loaded = set()

RETURN_SIGNAL = "__RETURN__"


# -----------------------------
# MATH PRECEDENCE
# -----------------------------
precedence = {
    "+": 1,
    "-": 1,
    "*": 2,
    "/": 2
}


# -----------------------------
# VALUE EVALUATION
# -----------------------------
def eval_value(value):
    value = str(value).strip()

    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]

    if value.startswith("%") and value.endswith("%"):
        return variables.get(value[1:-1], "")

    if value in variables:
        return variables[value]

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

        if line == "}":
            depth -= 1
            if depth == 0:
                return block, i
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

        if ch in "+-*/()":
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
# EXECUTOR
# -----------------------------
def execute(lines):
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


        # ---------------- IF ----------------
        if line.startswith("IF "):
            condition = line[3:].split("{")[0].strip()
            parts = condition.split()

            if len(parts) == 3:
                left, op, right = parts
                block, new_i = extract_block(lines, i + 1)

                if op in ops and ops[op](eval_value(left), eval_value(right)):
                    result = execute(block)
                    if result == RETURN_SIGNAL:
                        return RETURN_SIGNAL

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

                # restore variables ALWAYS
                variables.clear()
                variables.update(old_vars)

                # ONLY store return, never propagate exit unless explicitly top-level
                if result is not None and result != RETURN_SIGNAL:
                    variables["__return__"] = result

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
            var, value = line[4:].split("=", 1)
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