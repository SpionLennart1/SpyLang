# SpyLang Launcher - Better UI
# Recommended filename: SpyLang_Launcher.pyw
#
# Put this file next to spy.py and double-click it.
# Config is saved in: configs/spylang_launcher_config.json
#
# INPUT and WAITKEY both use the input bar.
# WAITKEY needs the patched spy.py that supports SPYLANG_LAUNCHER_CONSOLE=1.

import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path


APP_NAME = "SpyLang Launcher"
APP_VERSION = "v2.5-editor"
CONFIG_FOLDER = "configs"
CONFIG_NAME = "spylang_launcher_config.json"


def app_dir() -> Path:
    try:
        return Path(__file__).resolve().parent
    except Exception:
        return Path.cwd()


BASE_DIR = app_dir()
CONFIG_DIR = BASE_DIR / CONFIG_FOLDER
CONFIG_PATH = CONFIG_DIR / CONFIG_NAME


THEME = {
    "bg": "#0b0f17",
    "panel": "#111827",
    "panel2": "#151f2e",
    "panel3": "#1b2638",
    "console": "#05070c",
    "border": "#253044",
    "text": "#eef4ff",
    "muted": "#95a3b8",
    "accent": "#42e66b",
    "accent_dark": "#29b850",
    "danger": "#ff5c6a",
    "danger_dark": "#d94a56",
    "warning": "#ffd166",
    "blue": "#5dade2",
    "purple": "#9b7cff",
    "black": "#000000",
}


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))




def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config():
    default = {
        "spy_path": str(BASE_DIR / "spy.py"),
        "script_path": "",
        "recent_scripts": []
    }

    if not CONFIG_PATH.exists():
        return default

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        for key, value in default.items():
            if key not in data:
                data[key] = value

        return data
    except Exception:
        return default


def save_config(data):
    try:
        ensure_config_dir()
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass


def find_python_command():
    exe = Path(sys.executable)

    if exe.name.lower() == "pythonw.exe":
        python_exe = exe.with_name("python.exe")
        if python_exe.exists():
            return [str(python_exe)]

    if exe.exists() and exe.name.lower() != "pythonw.exe":
        return [str(exe)]

    py_launcher = shutil.which("py")
    if py_launcher:
        return [py_launcher]

    python_cmd = shutil.which("python")
    if python_cmd:
        return [python_cmd]

    return ["py"]


def make_button(parent, text, command, bg=None, hover=None, fg=None, width=None):
    bg = bg or THEME["panel3"]
    hover = hover or THEME["border"]
    fg = fg or THEME["text"]

    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg=fg,
        activebackground=hover,
        activeforeground=fg,
        relief="flat",
        bd=0,
        padx=14,
        pady=9,
        width=width,
        cursor="hand2",
        font=("Segoe UI", 10, "bold")
    )

    btn.bind("<Enter>", lambda e: btn.configure(bg=hover))
    btn.bind("<Leave>", lambda e: btn.configure(bg=bg))

    return btn


def make_entry(parent, var=None):
    return tk.Entry(
        parent,
        textvariable=var,
        bg=THEME["panel3"],
        fg=THEME["text"],
        insertbackground=THEME["text"],
        relief="flat",
        bd=0,
        font=("Cascadia Mono", 10),
        highlightthickness=1,
        highlightbackground=THEME["border"],
        highlightcolor=THEME["accent"]
    )


def make_label(parent, text, size=10, bold=False, muted=False, bg=None):
    return tk.Label(
        parent,
        text=text,
        bg=bg or THEME["bg"],
        fg=THEME["muted"] if muted else THEME["text"],
        font=("Segoe UI", size, "bold" if bold else "normal")
    )


class Card(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            bg=THEME["panel"],
            highlightthickness=1,
            highlightbackground=THEME["border"],
            bd=0,
            **kwargs
        )


class SpyLangLauncher(tk.Tk):
    def __init__(self):
        super().__init__()

        ensure_config_dir()
        self.config_data = load_config()

        self.process = None
        self.reader_thread = None
        self.output_queue = queue.Queue()
        self.ansi_buffer = ""
        self.script_card_widgets = []
        self.selected_script_path = None
        self.last_error_file = None
        self.last_error_line = None

        self.title(f"{APP_NAME} {APP_VERSION}")

        self.screen_w = self.winfo_screenwidth()
        self.screen_h = self.winfo_screenheight()
        self.compact_mode = self.screen_w < 1050 or self.screen_h < 720

        win_w = clamp(1180, 760, self.screen_w - 40)
        win_h = clamp(760, 500, self.screen_h - 80)

        if self.compact_mode:
            win_w = clamp(980, 720, self.screen_w - 30)
            win_h = clamp(640, 460, self.screen_h - 70)

        x = max(0, (self.screen_w - win_w) // 2)
        y = max(0, (self.screen_h - win_h) // 2)

        self.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.minsize(720, 460)
        self.configure(bg=THEME["bg"])

        self.spy_var = tk.StringVar(value=self.config_data.get("spy_path", ""))
        self.script_var = tk.StringVar(value=self.config_data.get("script_path", ""))
        self.search_var = tk.StringVar()
        self.input_var = tk.StringVar()

        self.build_ui()
        self.refresh_script_list()
        self.update_status()

        self.bind("<F11>", self.toggle_fullscreen)
        self.bind("<Escape>", self.exit_fullscreen)
        self.bind("<Control-l>", self.focus_input)
        self.bind("<Control-L>", self.focus_input)

        self.after(30, self.poll_output)

    def focus_input(self, event=None):
        try:
            self.input_entry.focus_set()
            self.input_entry.see("end")
        except Exception:
            pass
        return "break"

    def toggle_fullscreen(self, event=None):
        self.attributes("-fullscreen", not bool(self.attributes("-fullscreen")))
        return "break"

    def exit_fullscreen(self, event=None):
        self.attributes("-fullscreen", False)
        return "break"

    def build_ui(self):
        root = tk.Frame(self, bg=THEME["bg"])
        pad_x = 8 if self.compact_mode else 18
        pad_y = 8 if self.compact_mode else 16
        root.pack(fill="both", expand=True, padx=pad_x, pady=pad_y)

        self.build_header(root)

        body = tk.Frame(root, bg=THEME["bg"])
        body.pack(fill="both", expand=True, pady=((8 if self.compact_mode else 16), 0))

        left = Card(body)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8 if self.compact_mode else 12))

        right_width = 260 if self.compact_mode else 325
        right = Card(body, width=right_width)

        if self.screen_w >= 820:
            right.pack(side="right", fill="y")
            right.pack_propagate(False)
        else:
            self.right_hidden_small_screen = True

        self.build_left(left)
        self.build_right(right)

        self.build_status(root)

    def build_header(self, parent):
        header = tk.Frame(parent, bg=THEME["bg"])
        header.pack(fill="x")

        logo = tk.Frame(header, bg=THEME["bg"])
        logo.pack(side="left", fill="x", expand=True)

        icon = tk.Label(
            logo,
            text="🕵",
            bg=THEME["panel"],
            fg=THEME["accent"],
            font=("Segoe UI Emoji", 24),
            width=2,
            height=1,
            relief="flat"
        )
        icon.pack(side="left", padx=(0, 12))

        text_box = tk.Frame(logo, bg=THEME["bg"])
        text_box.pack(side="left")

        tk.Label(
            text_box,
            text="SpyLang Launcher",
            bg=THEME["bg"],
            fg=THEME["text"],
            font=("Segoe UI", 18 if self.compact_mode else 24, "bold")
        ).pack(anchor="w")

        if not self.compact_mode:
            tk.Label(
                text_box,
                text="Run .spy scripts with an embedded console, input bar, colors, and script explorer.",
                bg=THEME["bg"],
                fg=THEME["muted"],
                font=("Segoe UI", 10)
            ).pack(anchor="w", pady=(2, 0))

        make_button(header, "Open Folder", self.open_base_folder).pack(side="right", padx=(8, 0))
        make_button(header, "Refresh", self.refresh_all).pack(side="right", padx=(8, 0))

    def section_title(self, parent, text):
        tk.Label(
            parent,
            text=text,
            bg=THEME["panel"],
            fg=THEME["text"],
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w")

    def build_left(self, parent):
        top = tk.Frame(parent, bg=THEME["panel"])
        top.pack(fill="x", padx=(10 if self.compact_mode else 16), pady=(10 if self.compact_mode else 16))

        self.section_title(top, "Interpreter")

        spy_row = tk.Frame(top, bg=THEME["panel"])
        spy_row.pack(fill="x", pady=(5, 8 if self.compact_mode else 14))

        self.spy_entry = make_entry(spy_row, self.spy_var)
        self.spy_entry.pack(side="left", fill="x", expand=True, ipady=(4 if self.compact_mode else 7))

        make_button(spy_row, "Browse", self.browse_spy).pack(side="left", padx=(8, 0))
        make_button(spy_row, "Auto", self.auto_find_spy).pack(side="left", padx=(8, 0))

        self.section_title(top, "Script")

        script_row = tk.Frame(top, bg=THEME["panel"])
        script_row.pack(fill="x", pady=(5, 8 if self.compact_mode else 14))

        self.script_entry = make_entry(script_row, self.script_var)
        self.script_entry.pack(side="left", fill="x", expand=True, ipady=(4 if self.compact_mode else 7))

        make_button(script_row, "Browse", self.browse_script).pack(side="left", padx=(8, 0))

        controls = tk.Frame(top, bg=THEME["panel"])
        controls.pack(fill="x")

        make_button(
            controls,
            "▶ Run",
            self.run_embedded,
            bg=THEME["accent_dark"],
            hover=THEME["accent"],
            fg=THEME["black"]
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))

        make_button(
            controls,
            "■ Stop",
            self.stop_process,
            bg=THEME["danger_dark"],
            hover=THEME["danger"]
        ).pack(side="left", padx=(0, 8))

        make_button(controls, "Clear", self.clear_console).pack(side="left")

        console_wrap = tk.Frame(
            parent,
            bg=THEME["border"],
            highlightthickness=0,
            bd=0
        )
        console_wrap.pack(fill="both", expand=True, padx=(10 if self.compact_mode else 16), pady=(0, 8 if self.compact_mode else 14))

        console_header = tk.Frame(console_wrap, bg=THEME["panel2"])
        console_header.pack(fill="x")

        tk.Label(
            console_header,
            text="●",
            bg=THEME["panel2"],
            fg=THEME["danger"],
            font=("Segoe UI", 12, "bold")
        ).pack(side="left", padx=(10, 2), pady=5)

        tk.Label(
            console_header,
            text="●",
            bg=THEME["panel2"],
            fg=THEME["warning"],
            font=("Segoe UI", 12, "bold")
        ).pack(side="left", padx=2)

        tk.Label(
            console_header,
            text="●",
            bg=THEME["panel2"],
            fg=THEME["accent"],
            font=("Segoe UI", 12, "bold")
        ).pack(side="left", padx=2)

        tk.Label(
            console_header,
            text="Embedded Console",
            bg=THEME["panel2"],
            fg=THEME["muted"],
            font=("Segoe UI", 9, "bold")
        ).pack(side="left", padx=10)

        make_button(
            console_header,
            "All" if self.compact_mode else "Copy All",
            self.copy_console_all,
            bg=THEME["panel3"],
            hover=THEME["border"],
            fg=THEME["text"],
            width=8
        ).pack(side="right", padx=(4, 8), pady=4)

        make_button(
            console_header,
            "Copy",
            self.copy_console_selection,
            bg=THEME["panel3"],
            hover=THEME["border"],
            fg=THEME["text"],
            width=6
        ).pack(side="right", padx=4, pady=4)

        console_body = tk.Frame(console_wrap, bg=THEME["console"])
        console_body.pack(fill="both", expand=True, padx=1, pady=(0, 1))

        self.console = tk.Text(
            console_body,
            bg=THEME["console"],
            fg=THEME["text"],
            insertbackground=THEME["text"],
            relief="flat",
            wrap="word",
            font=("Cascadia Mono", 9 if self.compact_mode else 10),
            undo=False,
            state="disabled",
            height=8 if self.compact_mode else 16,
            padx=10,
            pady=10
        )
        self.console.pack(side="left", fill="both", expand=True)
        self.console.bind("<Control-c>", self.copy_console_selection)
        self.console.bind("<Control-C>", self.copy_console_selection)
        self.console.bind("<Control-a>", self.select_all_console)
        self.console.bind("<Control-A>", self.select_all_console)
        self.console.bind("<Button-3>", self.show_console_menu)

        scroll = tk.Scrollbar(
            console_body,
            command=self.console.yview,
            bg=THEME["panel2"],
            troughcolor=THEME["console"],
            activebackground=THEME["accent"],
            relief="flat"
        )
        scroll.pack(side="right", fill="y")
        self.console.configure(yscrollcommand=scroll.set)

        self.console.tag_configure("normal", foreground=THEME["text"])
        self.console.tag_configure("red", foreground=THEME["danger"])
        self.console.tag_configure("green", foreground=THEME["accent"])
        self.console.tag_configure("yellow", foreground=THEME["warning"])
        self.console.tag_configure("blue", foreground=THEME["blue"])
        self.console.tag_configure("input", foreground="#ffffff")
        self.console.tag_configure("muted", foreground=THEME["muted"])
        self.console.tag_configure("purple", foreground=THEME["purple"])

        self.console_menu = tk.Menu(
            self.console,
            tearoff=0,
            bg=THEME["panel2"],
            fg=THEME["text"],
            activebackground=THEME["accent_dark"],
            activeforeground=THEME["black"],
            relief="flat"
        )
        self.console_menu.add_command(label="Copy selected", command=self.copy_console_selection)
        self.console_menu.add_command(label="Copy all", command=self.copy_console_all)
        self.console_menu.add_separator()
        self.console_menu.add_command(label="Clear console", command=self.clear_console)

        input_card = tk.Frame(parent, bg=THEME["panel"])
        input_card.pack(side="bottom", fill="x", padx=(10 if self.compact_mode else 16), pady=(0, 8 if self.compact_mode else 16))
        self.input_card = input_card
        self.console_wrap = console_wrap

        tk.Label(
            input_card,
            text="Input",
            bg=THEME["panel"],
            fg=THEME["muted"],
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", pady=(0, 6))

        input_row = tk.Frame(input_card, bg=THEME["panel"])
        input_row.pack(fill="x")

        self.input_entry = make_entry(input_row, self.input_var)
        self.input_entry.configure(font=("Cascadia Mono", 10 if self.compact_mode else 11))
        self.input_entry.pack(side="left", fill="x", expand=True, ipady=(6 if self.compact_mode else 9))
        self.input_entry.bind("<Return>", self.on_input_enter)

        make_button(
            input_row,
            "Paste",
            self.paste_to_input,
            bg=THEME["panel3"],
            hover=THEME["border"],
            fg=THEME["text"],
            width=6
        ).pack(side="left", padx=(8, 0))

        make_button(
            input_row,
            "Send",
            self.send_input,
            bg=THEME["accent_dark"],
            hover=THEME["accent"],
            fg=THEME["black"]
        ).pack(side="left", padx=(8, 0))

        # Keep the input bar pinned like a footer.
        # Pack order matters in Tkinter: reserve bottom input space first,
        # then let the console take only the remaining space.
        self.console_wrap.pack_forget()
        self.input_card.pack_forget()

        self.input_card.pack(
            side="bottom",
            fill="x",
            padx=(10 if self.compact_mode else 16),
            pady=(0, 8 if self.compact_mode else 16)
        )

        self.console_wrap.pack(
            side="top",
            fill="both",
            expand=True,
            padx=(10 if self.compact_mode else 16),
            pady=(0, 6 if self.compact_mode else 10)
        )

        self.write_console("SpyLang Launcher ready.\n", "green")
        self.write_console("Input bar is pinned to the bottom so it stays visible on smaller screens.\n", "muted")
        self.write_console("Use the input bar for INPUT and WAITKEY.\n", "muted")
        self.write_console("Copy output with Ctrl+C, right-click, or Copy All.\n\n", "muted")

    def build_right(self, parent):
        inner = tk.Frame(parent, bg=THEME["panel"])
        inner.pack(fill="both", expand=True, padx=(10 if self.compact_mode else 14), pady=(10 if self.compact_mode else 14))

        tk.Label(
            inner,
            text="Scripts",
            bg=THEME["panel"],
            fg=THEME["text"],
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w")

        tk.Label(
            inner,
            text="Double-click a script to run it.",
            bg=THEME["panel"],
            fg=THEME["muted"],
            font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(2, 10))

        self.search_entry = make_entry(inner, self.search_var)
        self.search_entry.configure(font=("Segoe UI", 10))
        self.search_entry.pack(fill="x", ipady=8)
        self.search_var.trace_add("write", lambda *_: self.refresh_script_list())

        list_wrap = tk.Frame(inner, bg=THEME["border"])
        list_wrap.pack(fill="both", expand=True, pady=(12, 12))

        self.script_canvas = tk.Canvas(
            list_wrap,
            bg=THEME["console"],
            highlightthickness=0,
            bd=0
        )
        self.script_canvas.pack(side="left", fill="both", expand=True, padx=1, pady=1)

        scroll = tk.Scrollbar(
            list_wrap,
            command=self.script_canvas.yview,
            bg=THEME["panel2"],
            troughcolor=THEME["console"],
            activebackground=THEME["accent"],
            relief="flat"
        )
        scroll.pack(side="right", fill="y", pady=1, padx=(0, 1))

        self.script_canvas.configure(yscrollcommand=scroll.set)

        self.script_cards_frame = tk.Frame(self.script_canvas, bg=THEME["console"])
        self.script_canvas_window = self.script_canvas.create_window(
            (0, 0),
            window=self.script_cards_frame,
            anchor="nw"
        )

        self.script_cards_frame.bind(
            "<Configure>",
            lambda event: self.script_canvas.configure(scrollregion=self.script_canvas.bbox("all"))
        )

        self.script_canvas.bind(
            "<Configure>",
            lambda event: self.script_canvas.itemconfigure(self.script_canvas_window, width=event.width)
        )

        self.script_canvas.bind("<MouseWheel>", self.on_script_mousewheel)
        self.script_cards_frame.bind("<MouseWheel>", self.on_script_mousewheel)

        make_button(inner, "Refresh List", self.refresh_script_list).pack(fill="x", pady=(0, 8))
        make_button(inner, "Built-in Editor", self.open_builtin_editor).pack(fill="x", pady=(0, 8))
        make_button(inner, "Open Last Error", self.open_last_error).pack(fill="x", pady=(0, 8))
        make_button(inner, "Open in Notepad", self.open_in_notepad).pack(fill="x", pady=(0, 8))
        make_button(inner, "Open Script Folder", self.open_script_folder).pack(fill="x", pady=(0, 8))
        make_button(inner, "Create Starter File", self.create_starter_file).pack(fill="x")

        info = tk.Frame(inner, bg=THEME["panel2"])
        info.pack(fill="x", pady=(14, 0))

        tk.Label(
            info,
            text="Launcher Mode",
            bg=THEME["panel2"],
            fg=THEME["accent"],
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=10, pady=(8, 0))

        tk.Label(
            info,
            text="INPUT and WAITKEY both use the input bar. WAITKEY needs the patched spy.py.",
            bg=THEME["panel2"],
            fg=THEME["muted"],
            font=("Segoe UI", 9),
            wraplength=270,
            justify="left"
        ).pack(anchor="w", padx=10, pady=(4, 10))

    def build_status(self, parent):
        bar = tk.Frame(parent, bg=THEME["bg"])
        bar.pack(fill="x", pady=(10, 0))

        self.status_dot = tk.Label(
            bar,
            text="●",
            bg=THEME["bg"],
            fg=THEME["muted"],
            font=("Segoe UI", 12, "bold")
        )
        self.status_dot.pack(side="left")

        self.status_label = tk.Label(
            bar,
            text="",
            bg=THEME["bg"],
            fg=THEME["muted"],
            font=("Segoe UI", 9)
        )
        self.status_label.pack(side="left", padx=(6, 0))

        tk.Label(
            bar,
            text="Config: configs/spylang_launcher_config.json",
            bg=THEME["bg"],
            fg=THEME["muted"],
            font=("Segoe UI", 9)
        ).pack(side="right")

    def copy_console_selection(self, event=None):
        try:
            selected = self.console.get("sel.first", "sel.last")
        except tk.TclError:
            return "break"

        self.clipboard_clear()
        self.clipboard_append(selected)
        self.update()

        return "break"

    def copy_console_all(self, event=None):
        text = self.console.get("1.0", "end-1c")

        if text == "":
            return "break"

        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()

        return "break"

    def select_all_console(self, event=None):
        self.console.tag_add("sel", "1.0", "end-1c")
        self.console.mark_set("insert", "1.0")
        self.console.see("1.0")

        return "break"

    def show_console_menu(self, event):
        try:
            self.console_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.console_menu.grab_release()

        return "break"

    def paste_to_input(self):
        try:
            text = self.clipboard_get()
        except tk.TclError:
            return

        self.input_entry.focus_set()
        self.input_entry.insert("insert", text)

    def detect_error_location(self, text):
        try:
            file_match = re.search(r"File:\s*(.+)", text)
            line_match = re.search(r"Line:\s*(\d+)", text)

            if file_match:
                path = file_match.group(1).strip()
                if path and path != "<script>":
                    self.last_error_file = Path(path)

            if line_match:
                self.last_error_line = int(line_match.group(1))
        except Exception:
            pass

    def open_last_error(self):
        if not self.last_error_file or not self.last_error_file.exists():
            messagebox.showinfo("No error", "No saved SpyLang error location yet.")
            return

        self.open_builtin_editor(path=self.last_error_file, goto_line=self.last_error_line)

    def open_builtin_editor(self, path=None, goto_line=None):
        if path is None:
            current = self.script_var.get().strip()
            if not current:
                messagebox.showwarning("No script", "Select a .spy file first.")
                return
            path = Path(current)

        if not path.exists():
            messagebox.showerror("Missing file", "The selected script does not exist.")
            return

        win = tk.Toplevel(self)
        win.title("SpyLang Editor - " + path.name)
        win.geometry("900x650")
        win.minsize(560, 360)
        win.configure(bg=THEME["bg"])

        top = tk.Frame(win, bg=THEME["panel"])
        top.pack(side="top", fill="x")

        title = tk.Label(top, text=str(path), bg=THEME["panel"], fg=THEME["muted"], anchor="w")
        title.pack(side="left", fill="x", expand=True, padx=10, pady=8)

        editor_wrap = tk.Frame(win, bg=THEME["console"])
        editor_wrap.pack(side="top", fill="both", expand=True, padx=8, pady=8)

        text = tk.Text(
            editor_wrap,
            bg=THEME["console"],
            fg=THEME["text"],
            insertbackground=THEME["text"],
            relief="flat",
            wrap="none",
            font=("Cascadia Mono", 11),
            undo=True,
            padx=10,
            pady=10
        )
        text.pack(side="left", fill="both", expand=True)

        yscroll = tk.Scrollbar(editor_wrap, orient="vertical", command=text.yview)
        yscroll.pack(side="right", fill="y")
        text.configure(yscrollcommand=yscroll.set)

        xscroll = tk.Scrollbar(win, orient="horizontal", command=text.xview)
        xscroll.pack(side="bottom", fill="x")
        text.configure(xscrollcommand=xscroll.set)

        try:
            text.insert("1.0", path.read_text(encoding="utf-8"))
        except Exception as e:
            messagebox.showerror("Open failed", str(e))
            win.destroy()
            return

        text.tag_configure("cmd", foreground=THEME["accent"])
        text.tag_configure("str", foreground=THEME["warning"])
        text.tag_configure("comment", foreground=THEME["muted"])
        text.tag_configure("errorline", background="#3a1820")

        commands = [
            "LET", "PRINT", "INPUT", "IF", "ELSEIF", "ELSE", "WHILE", "FOR", "REPEAT", "FOREACH",
            "FUNC", "CALL", "RETURN", "GLOBAL", "BREAK", "EXIT", "IMPORT", "AICHOICE", "AICHANCE",
            "AIWEIGHTED", "AIPATH", "DRAWMAP", "GETTILE", "SETTILE", "MOVEPLAYER", "SAVESLOT",
            "LOADSLOT", "QUESTADD", "XPADD", "SHOPBUY", "ENEMYNEW", "VERSION", "HELP"
        ]

        def highlight(event=None):
            text.tag_remove("cmd", "1.0", "end")
            text.tag_remove("str", "1.0", "end")
            text.tag_remove("comment", "1.0", "end")

            content = text.get("1.0", "end-1c")
            for idx, line in enumerate(content.splitlines(), start=1):
                stripped = line.lstrip()
                leading = len(line) - len(stripped)
                first = stripped.split(" ", 1)[0] if stripped else ""
                if first in commands:
                    start = f"{idx}.{leading}"
                    end = f"{idx}.{leading + len(first)}"
                    text.tag_add("cmd", start, end)

                comment_pos = line.find("#")
                if comment_pos >= 0:
                    text.tag_add("comment", f"{idx}.{comment_pos}", f"{idx}.end")

                for match in re.finditer(r'"[^"\\]*(?:\\.[^"\\]*)*"', line):
                    text.tag_add("str", f"{idx}.{match.start()}", f"{idx}.{match.end()}")

        def save_file():
            try:
                path.write_text(text.get("1.0", "end-1c"), encoding="utf-8")
                self.write_console("Saved: " + str(path) + "\n", "green")
                self.refresh_script_list()
            except Exception as e:
                messagebox.showerror("Save failed", str(e))

        def save_and_run():
            save_file()
            self.set_script(path)
            win.destroy()
            self.run_embedded()

        make_button(top, "Save", save_file).pack(side="right", padx=4, pady=5)
        make_button(top, "Save + Run", save_and_run).pack(side="right", padx=4, pady=5)
        make_button(top, "Close", win.destroy).pack(side="right", padx=4, pady=5)

        text.bind("<KeyRelease>", highlight)
        highlight()

        if goto_line:
            line = max(1, int(goto_line))
            text.tag_add("errorline", f"{line}.0", f"{line}.end")
            text.mark_set("insert", f"{line}.0")
            text.see(f"{line}.0")

        text.focus_set()

    def write_console(self, text, tag="normal"):
        self.detect_error_location(text)
        self.console.configure(state="normal")
        self.console.insert("end", text, tag)
        self.console.configure(state="disabled")
        self.console.see("end")

    def append_ansi(self, text):
        data = self.ansi_buffer + text
        self.ansi_buffer = ""

        current_tag = "normal"
        i = 0

        self.console.configure(state="normal")

        while i < len(data):
            if data[i] == "\x1b":
                match = re.match(r"\x1b\[(\d+)m", data[i:])

                if match:
                    code = match.group(1)

                    if code == "31":
                        current_tag = "red"
                    elif code == "32":
                        current_tag = "green"
                    elif code == "33":
                        current_tag = "yellow"
                    elif code == "34":
                        current_tag = "blue"
                    elif code == "35":
                        current_tag = "purple"
                    elif code == "0":
                        current_tag = "normal"

                    i += len(match.group(0))
                    continue

                if i > len(data) - 6:
                    self.ansi_buffer = data[i:]
                    break

            self.console.insert("end", data[i], current_tag)
            i += 1

        self.console.configure(state="disabled")
        self.console.see("end")

    def clear_console(self):
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")

    def validate_paths(self):
        spy = Path(self.spy_var.get().strip())
        script = Path(self.script_var.get().strip())

        if not spy.exists():
            messagebox.showerror("Missing spy.py", "spy.py was not found. Select the correct interpreter file.")
            return None, None

        if not script.exists():
            messagebox.showerror("Missing .spy file", "The selected .spy script was not found.")
            return None, None

        return spy, script

    def run_embedded(self):
        spy, script = self.validate_paths()
        if not spy or not script:
            self.update_status()
            return

        if self.process and self.process.poll() is None:
            messagebox.showwarning("Already running", "A SpyLang script is already running. Stop it first.")
            return

        self.save_current_config()
        self.clear_console()

        python_args = find_python_command()
        args = python_args + ["-u", str(spy), str(script)]

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["SPYLANG_LAUNCHER_CONSOLE"] = "1"

        self.write_console("Running script\n", "green")
        self.write_console("Python: " + " ".join(python_args) + "\n", "muted")
        self.write_console("Interpreter: " + str(spy) + "\n", "muted")
        self.write_console("Script: " + str(script) + "\n\n", "muted")

        try:
            creationflags = 0
            startupinfo = None

            if os.name == "nt":
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

                try:
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = 0
                except Exception:
                    startupinfo = None

            self.process = subprocess.Popen(
                args,
                cwd=str(script.parent),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=0,
                env=env,
                creationflags=creationflags,
                startupinfo=startupinfo
            )

            self.reader_thread = threading.Thread(target=self.reader_loop, daemon=True)
            self.reader_thread.start()
            self.input_entry.focus_force()
            self.update_status()

        except Exception as e:
            messagebox.showerror("Launch failed", str(e))
            self.write_console("ERROR: " + str(e) + "\n", "red")
            self.process = None
            self.update_status()

    def reader_loop(self):
        try:
            while True:
                if self.process is None:
                    break

                ch = self.process.stdout.read(1)

                if ch == "":
                    break

                self.output_queue.put(ch)
        except Exception as e:
            self.output_queue.put("\n[Launcher read error: " + str(e) + "]\n")

        self.output_queue.put("\n[Program finished]\n")

    def poll_output(self):
        chunks = []

        try:
            while True:
                chunks.append(self.output_queue.get_nowait())
        except queue.Empty:
            pass

        if chunks:
            self.append_ansi("".join(chunks))

        self.after(30, self.poll_output)

    def on_input_enter(self, event=None):
        self.send_input()
        return "break"

    def send_input(self):
        try:
            self.input_entry.focus_set()
        except Exception:
            pass

        text = self.input_var.get()
        self.input_var.set("")

        if not self.process or self.process.poll() is not None:
            self.write_console("No script is running.\n", "red")
            return

        try:
            self.process.stdin.write(text + "\n")
            self.process.stdin.flush()
            self.write_console(text + "\n", "input")
        except Exception as e:
            self.write_console("Input error: " + str(e) + "\n", "red")

    def stop_process(self):
        if not self.process or self.process.poll() is not None:
            self.write_console("No script is running.\n", "muted")
            return

        try:
            self.process.terminate()
            self.write_console("\n[Program stopped]\n", "red")
        except Exception as e:
            self.write_console("Stop error: " + str(e) + "\n", "red")

    def refresh_all(self):
        self.refresh_script_list()
        self.update_status()
        self.write_console("Refreshed.\n", "muted")

    def auto_find_spy(self):
        candidates = []

        for path in [BASE_DIR / "spy.py", Path.cwd() / "spy.py"]:
            if path.exists():
                candidates.append(path)

        if not candidates:
            for found in BASE_DIR.rglob("spy.py"):
                candidates.append(found)
                break

        if candidates:
            self.spy_var.set(str(candidates[0]))
            self.save_current_config()
            self.update_status()
            self.write_console("Found spy.py: " + str(candidates[0]) + "\n", "muted")
        else:
            messagebox.showwarning("spy.py not found", "Could not find spy.py. Browse for it.")

    def browse_spy(self):
        path = filedialog.askopenfilename(
            title="Select spy.py",
            initialdir=str(BASE_DIR),
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )

        if path:
            self.spy_var.set(path)
            self.save_current_config()
            self.update_status()

    def browse_script(self):
        path = filedialog.askopenfilename(
            title="Select SpyLang script",
            initialdir=str(BASE_DIR),
            filetypes=[("SpyLang files", "*.spy"), ("All files", "*.*")]
        )

        if path:
            self.set_script(path)

    def set_script(self, path):
        self.script_var.set(str(path))

        recent = self.config_data.get("recent_scripts", [])
        path_text = str(path)

        if path_text in recent:
            recent.remove(path_text)

        recent.insert(0, path_text)
        self.config_data["recent_scripts"] = recent[:10]
        self.save_current_config()
        self.update_status()

        try:
            self.selected_script_path = Path(path)
            self.update_script_card_styles()
        except Exception:
            pass

    def save_current_config(self):
        self.config_data["spy_path"] = self.spy_var.get()
        self.config_data["script_path"] = self.script_var.get()
        save_config(self.config_data)

    def update_status(self):
        spy = Path(self.spy_var.get())
        script = Path(self.script_var.get()) if self.script_var.get() else None

        running = self.process is not None and self.process.poll() is None

        text = "Python: " + " ".join(find_python_command())

        if spy.exists():
            text += "  |  spy.py: OK"
        else:
            text += "  |  spy.py: missing"

        if script and script.exists():
            text += "  |  script: OK"
        else:
            text += "  |  script: not selected"

        if running:
            text += "  |  running"
            self.status_dot.configure(fg=THEME["accent"])
        else:
            self.status_dot.configure(fg=THEME["muted"])

        self.status_label.configure(text=text)

    def get_all_scripts(self):
        scripts = []

        try:
            for path in BASE_DIR.rglob("*.spy"):
                if path.is_file():
                    scripts.append(path)
        except Exception:
            pass

        scripts.sort(key=lambda p: str(p).lower())
        return scripts

    def refresh_script_list(self):
        search = self.search_var.get().lower().strip()
        self.list_paths = []

        for child in self.script_cards_frame.winfo_children():
            child.destroy()

        self.script_card_widgets = []

        for path in self.get_all_scripts():
            try:
                rel = path.relative_to(BASE_DIR)
            except Exception:
                rel = path

            display = str(rel).replace("\\", "/")

            if search and search not in display.lower():
                continue

            self.list_paths.append(path)
            self.add_script_card(path, display)

        if not self.list_paths:
            empty = tk.Label(
                self.script_cards_frame,
                text="No .spy files found",
                bg=THEME["console"],
                fg=THEME["muted"],
                font=("Segoe UI", 10, "bold")
            )
            empty.pack(fill="x", padx=10, pady=18)

    def add_script_card(self, path, display):
        folder = str(Path(display).parent).replace("\\", "/")
        if folder == ".":
            folder = "root"

        filename = Path(display).name

        card = tk.Frame(
            self.script_cards_frame,
            bg=THEME["panel2"],
            highlightthickness=1,
            highlightbackground=THEME["border"],
            bd=0,
            cursor="hand2"
        )
        card.pack(fill="x", padx=8, pady=(8, 0))

        inner = tk.Frame(card, bg=THEME["panel2"], cursor="hand2")
        inner.pack(fill="x", padx=10, pady=9)

        icon = tk.Label(
            inner,
            text="◆",
            bg=THEME["panel2"],
            fg=THEME["accent"],
            font=("Segoe UI", 13, "bold"),
            cursor="hand2"
        )
        icon.pack(side="left", padx=(0, 9))

        text_box = tk.Frame(inner, bg=THEME["panel2"], cursor="hand2")
        text_box.pack(side="left", fill="x", expand=True)

        name_label = tk.Label(
            text_box,
            text=filename,
            bg=THEME["panel2"],
            fg=THEME["text"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            cursor="hand2"
        )
        name_label.pack(fill="x")

        folder_label = tk.Label(
            text_box,
            text=folder,
            bg=THEME["panel2"],
            fg=THEME["muted"],
            font=("Segoe UI", 8),
            anchor="w",
            cursor="hand2"
        )
        folder_label.pack(fill="x", pady=(2, 0))

        run_badge = tk.Label(
            inner,
            text="RUN",
            bg=THEME["panel3"],
            fg=THEME["muted"],
            font=("Segoe UI", 8, "bold"),
            padx=7,
            pady=3,
            cursor="hand2"
        )
        run_badge.pack(side="right", padx=(8, 0))

        widgets = [card, inner, icon, text_box, name_label, folder_label, run_badge]

        for widget in widgets:
            widget.bind("<Button-1>", lambda event, p=path: self.select_script_card_event(p))
            widget.bind("<Double-Button-1>", lambda event, p=path: self.run_script_card_event(p))
            widget.bind("<Enter>", lambda event, items=widgets: self.hover_script_card(items, True))
            widget.bind("<Leave>", lambda event, items=widgets: self.hover_script_card(items, False))
            widget.bind("<MouseWheel>", self.on_script_mousewheel)

        self.script_card_widgets.append({
            "path": path,
            "widgets": widgets,
            "card": card,
            "inner": inner,
            "icon": icon,
            "text_box": text_box,
            "name": name_label,
            "folder": folder_label,
            "badge": run_badge
        })

        self.update_script_card_styles()

    def hover_script_card(self, widgets, active):
        path = None
        for item in self.script_card_widgets:
            if item["widgets"] == widgets:
                path = item["path"]
                break

        if path == self.selected_script_path:
            return

        bg = THEME["panel3"] if active else THEME["panel2"]

        for widget in widgets:
            try:
                widget.configure(bg=bg)
            except Exception:
                pass

    def select_script_card_event(self, path):
        self.select_script_card(path)
        return "break"

    def run_script_card_event(self, path):
        self.run_script_card(path)
        return "break"

    def select_script_card(self, path):
        self.selected_script_path = Path(path)
        self.set_script(path)
        self.update_script_card_styles()

        try:
            self.input_entry.focus_set()
        except Exception:
            pass

    def run_script_card(self, path):
        self.select_script_card(path)
        self.run_embedded()

    def update_script_card_styles(self):
        for item in self.script_card_widgets:
            selected = item["path"] == self.selected_script_path or str(item["path"]) == self.script_var.get()

            bg = THEME["accent_dark"] if selected else THEME["panel2"]
            fg = THEME["black"] if selected else THEME["text"]
            muted = "#102615" if selected else THEME["muted"]
            icon_fg = THEME["black"] if selected else THEME["accent"]
            badge_bg = THEME["accent"] if selected else THEME["panel3"]
            badge_fg = THEME["black"] if selected else THEME["muted"]

            for key in ["card", "inner", "text_box"]:
                item[key].configure(bg=bg)

            item["icon"].configure(bg=bg, fg=icon_fg)
            item["name"].configure(bg=bg, fg=fg)
            item["folder"].configure(bg=bg, fg=muted)
            item["badge"].configure(bg=badge_bg, fg=badge_fg)

    def on_script_mousewheel(self, event):
        try:
            self.script_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    def on_script_select(self, event=None):
        pass

    def open_base_folder(self):
        self.open_folder(BASE_DIR)

    def open_script_folder(self):
        script = Path(self.script_var.get().strip())

        if script.exists():
            self.open_folder(script.parent)
        else:
            self.open_folder(BASE_DIR)

    def open_folder(self, path):
        try:
            if os.name == "nt":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as e:
            self.write_console("Could not open folder: " + str(e) + "\n", "red")

    def open_in_notepad(self):
        script = Path(self.script_var.get().strip())

        if not script.exists():
            messagebox.showwarning("No script selected", "Select a .spy file first.")
            return

        try:
            if os.name == "nt":
                subprocess.Popen(["notepad.exe", str(script)])
            else:
                subprocess.Popen([sys.executable, "-m", "idlelib", str(script)])
        except Exception as e:
            self.write_console("Could not open editor: " + str(e) + "\n", "red")

    def create_starter_file(self):
        path = filedialog.asksaveasfilename(
            title="Create SpyLang starter file",
            initialdir=str(BASE_DIR),
            defaultextension=".spy",
            filetypes=[("SpyLang files", "*.spy")]
        )

        if not path:
            return

        starter = (
            'CLS\n\n'
            'PRINT GREEN "Hello from SpyLang!"\n'
            'PRINT "Enter your name:"\n'
            'INPUT name\n\n'
            'PRINT "Welcome:"\n'
            'PRINT %name%\n\n'
            'LET roll = RANDOM 1 6\n'
            'PRINT "You rolled:"\n'
            'PRINT %roll%\n\n'
            'IF roll == 6 {\n'
            '    PRINT GREEN "Lucky roll!"\n'
            '}\n'
            'ELSE {\n'
            '    PRINT YELLOW "Normal roll."\n'
            '}\n\n'
            'PAUSE\n'
        )

        try:
            Path(path).write_text(starter, encoding="utf-8")
            self.refresh_script_list()
            self.set_script(path)
            self.write_console("Created starter file: " + str(path) + "\n", "muted")
        except Exception as e:
            messagebox.showerror("Could not create file", str(e))

    def on_close(self):
        if self.process and self.process.poll() is None:
            if messagebox.askyesno("Script is running", "A script is still running. Stop it and close?"):
                self.stop_process()
            else:
                return

        self.destroy()


if __name__ == "__main__":
    app = SpyLangLauncher()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
