# SpyLang Launcher v3
# Recommended filename: SpyLang_Launcher.pyw
#
# Put this file next to spy.py and double-click it.
# v3 changes:
# - Custom dark title bar
# - Console / Editor / Scripts / Settings tabs
# - Better integrated editor
# - Auto-hidden dark scrollbars
# - Fixed input bar
# - Click/open last error helper

import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
import ctypes
from tkinter import filedialog, messagebox
from pathlib import Path


APP_NAME = "SpyLang Launcher"
APP_VERSION = "v3.0-launcher-stable"
CONFIG_FOLDER = "configs"
CONFIG_NAME = "spylang_launcher_config.json"


THEME = {
    "bg": "#070b12",
    "title": "#05070c",
    "panel": "#101827",
    "panel2": "#141f30",
    "panel3": "#1b293d",
    "console": "#03050a",
    "editor": "#070b12",
    "border": "#26364f",
    "text": "#eef4ff",
    "muted": "#91a0b8",
    "accent": "#42e66b",
    "accent_dark": "#24b84d",
    "danger": "#ff5c6a",
    "danger_dark": "#d94a56",
    "warning": "#ffd166",
    "blue": "#5dade2",
    "purple": "#9b7cff",
    "black": "#000000",
}


KEYWORDS = {
    "PRINT", "GREEN", "RED", "YELLOW", "BLUE", "LET", "INPUT", "IF", "ELSEIF", "ELSE",
    "WHILE", "BREAK", "REPEAT", "FOR", "TO", "STEP", "FOREACH", "FUNC", "CALL", "RETURN",
    "GLOBAL", "IMPORT", "EXIT", "PUSH", "POP", "SET", "CLEAR", "LEN", "SAVEVAR", "LOADVAR",
    "WRITEFILE", "READFILE", "SAVESLOT", "LOADSLOT", "DELSLOT", "LISTSLOTS", "SLOTMENU",
    "DRAWMAP", "MAPSIZE", "GETTILE", "SETTILE", "FINDPOS", "CANMOVE", "MOVEPLAYER",
    "DISTANCE", "MAPTRANS", "MAPFILL", "MAPBORDER", "MAPRECT", "MAPLINE", "MAPCOPY",
    "MAPPASTE", "MAPREPLACE", "MAPCOUNT", "MAPFINDALL", "VIEWPORT", "LOADMAP", "SAVEMAP",
    "MENUCREATE", "MENUADD", "MENUCLEAR", "MENUDRAW", "MENUCOUNT", "MENUSHOW", "SELECTLIST",
    "CONFIRM", "PROMPT", "EVENTSET", "EVENTGET", "EVENTCLEAR", "EVENTEXISTS", "EVENTONCE",
    "TRIGGER", "ONTRIGGER", "HOST", "CONNECT", "SEND", "RECEIVE", "TRYRECEIVE", "PING",
    "BROADCAST", "DISCONNECT", "VERSION", "CLS", "PAUSE", "SLEEP", "WAITKEY"
}


def app_dir() -> Path:
    try:
        return Path(__file__).resolve().parent
    except Exception:
        return Path.cwd()


BASE_DIR = app_dir()
CONFIG_DIR = BASE_DIR / CONFIG_FOLDER
CONFIG_PATH = CONFIG_DIR / CONFIG_NAME


def ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config():
    default = {
        "spy_path": str(BASE_DIR / "spy.py"),
        "script_path": "",
        "recent_scripts": [],
        "window_geometry": "",
        "active_tab": "Console"
    }

    if not CONFIG_PATH.exists():
        return default

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, value in default.items():
            data.setdefault(key, value)
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


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


class AutoHideScrollbar(tk.Scrollbar):
    def set(self, first, last):
        try:
            first_f = float(first)
            last_f = float(last)
            if first_f <= 0.0 and last_f >= 1.0:
                self.grid_remove()
            else:
                self.grid()
        except Exception:
            self.grid()
        super().set(first, last)


class HoverButton(tk.Label):
    def __init__(self, parent, text, command=None, bg=None, hover=None, fg=None, font=None, padx=12, pady=8):
        self.normal_bg = bg or THEME["panel3"]
        self.hover_bg = hover or THEME["border"]
        self.command = command
        super().__init__(
            parent,
            text=text,
            bg=self.normal_bg,
            fg=fg or THEME["text"],
            font=font or ("Segoe UI", 10, "bold"),
            padx=padx,
            pady=pady,
            cursor="hand2"
        )
        self.bind("<Enter>", lambda e: self.configure(bg=self.hover_bg))
        self.bind("<Leave>", lambda e: self.configure(bg=self.normal_bg))
        self.bind("<Button-1>", self._clicked)

    def _clicked(self, event=None):
        if self.command:
            self.command()


class SpyLangLauncher(tk.Tk):
    def __init__(self):
        super().__init__()

        ensure_config_dir()
        self.config_data = load_config()

        self.process = None
        self.reader_thread = None
        self.output_queue = queue.Queue()
        self.current_ansi_tag = "normal"
        self.is_maximized = False
        self.restore_geometry = ""
        self.drag_x = 0
        self.drag_y = 0
        self.active_tab = None
        self.tab_buttons = {}
        self.pages = {}
        self.script_card_widgets = []
        self.selected_script_path = None
        self.last_error_file = None
        self.last_error_line = None
        self.editor_file = None
        self.highlight_job = None

        self.spy_var = tk.StringVar(value=self.config_data.get("spy_path", str(BASE_DIR / "spy.py")))
        self.script_var = tk.StringVar(value=self.config_data.get("script_path", ""))
        self.search_var = tk.StringVar()
        self.input_var = tk.StringVar()
        self.editor_path_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="")

        self.configure(bg=THEME["bg"])
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.after_idle(self.apply_windows_dark_titlebar)
        self.after(300, self.apply_windows_dark_titlebar)
        self.after(1200, self.apply_windows_dark_titlebar)
        self.after(100, self.apply_windows_dark_titlebar)

        self.screen_w = self.winfo_screenwidth()
        self.screen_h = self.winfo_screenheight()

        if self.config_data.get("window_geometry"):
            self.geometry(self.config_data["window_geometry"])
        else:
            win_w = clamp(1180, 820, self.screen_w - 60)
            win_h = clamp(760, 560, self.screen_h - 80)
            x = max(0, (self.screen_w - win_w) // 2)
            y = max(0, (self.screen_h - win_h) // 2)
            self.geometry(f"{win_w}x{win_h}+{x}+{y}")

        self.minsize(780, 520)

        self.build_ui()
        self.refresh_script_list()
        self.update_status()

        self.bind("<F11>", self.toggle_fullscreen)
        self.bind("<Escape>", self.exit_fullscreen)
        self.bind("<Control-r>", lambda e: self.run_embedded())
        self.bind("<Control-R>", lambda e: self.run_embedded())
        self.bind("<Control-s>", lambda e: self.save_editor())
        self.bind("<Control-S>", lambda e: self.save_editor())
        self.bind("<Control-l>", lambda e: self.focus_input())
        self.bind("<Control-L>", lambda e: self.focus_input())
        self.bind("<FocusIn>", lambda e: self.apply_windows_dark_titlebar())

        self.after(30, self.poll_output)

        start_tab = self.config_data.get("active_tab", "Console")
        if start_tab not in ["Console", "Editor", "Scripts", "Settings"]:
            start_tab = "Console"
        self.show_tab(start_tab)

    def build_ui(self):
        self.outer = tk.Frame(self, bg=THEME["border"], bd=0)
        self.outer.pack(fill="both", expand=True)

        self.build_title_bar(self.outer)

        self.body = tk.Frame(self.outer, bg=THEME["bg"])
        self.body.pack(fill="both", expand=True, padx=1, pady=(0, 1))

        self.build_tab_bar(self.body)

        self.page_holder = tk.Frame(self.body, bg=THEME["bg"])
        self.page_holder.pack(fill="both", expand=True)

        self.build_console_page()
        self.build_editor_page()
        self.build_scripts_page()
        self.build_settings_page()

        self.build_status_bar(self.body)

        self.write_console("SpyLang Launcher v3 ready.\n", "green")
        self.write_console("Tabs: Console / Editor / Scripts / Settings.\n", "muted")
        self.write_console("Stable Windows mode enabled: taskbar works, no Explorer bugs.\n\n", "muted")

    def build_title_bar(self, parent):
        # Stable version: keep the real Windows title bar.
        # This guarantees normal taskbar/Alt-Tab/minimize/close behavior.
        bar = tk.Frame(parent, bg=THEME["title"], height=58)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        left = tk.Frame(bar, bg=THEME["title"])
        left.pack(side="left", fill="x", expand=True)

        icon = tk.Label(
            left,
            text="🕵",
            bg=THEME["title"],
            fg=THEME["accent"],
            font=("Segoe UI Emoji", 20)
        )
        icon.pack(side="left", padx=(16, 10))

        text_box = tk.Frame(left, bg=THEME["title"])
        text_box.pack(side="left", fill="x", expand=True)

        title = tk.Label(
            text_box,
            text=APP_NAME,
            bg=THEME["title"],
            fg=THEME["text"],
            font=("Segoe UI", 13, "bold"),
            anchor="w"
        )
        title.pack(anchor="w", pady=(8, 0))

        subtitle = tk.Label(
            text_box,
            text=f"{APP_VERSION}  •  stable Windows window mode",
            bg=THEME["title"],
            fg=THEME["muted"],
            font=("Segoe UI", 9),
            anchor="w"
        )
        subtitle.pack(anchor="w")

        tk.Label(
            bar,
            text="Use the normal Windows buttons at the top-right",
            bg=THEME["title"],
            fg=THEME["muted"],
            font=("Segoe UI", 9)
        ).pack(side="right", padx=16)

    def build_tab_bar(self, parent):
        wrap = tk.Frame(parent, bg=THEME["bg"])
        wrap.pack(fill="x", padx=14, pady=(12, 0))

        for name, label in [
            ("Console", "▶ Console"),
            ("Editor", "✎ Editor"),
            ("Scripts", "◆ Scripts"),
            ("Settings", "⚙ Settings"),
        ]:
            btn = HoverButton(wrap, label, command=lambda n=name: self.show_tab(n), bg=THEME["panel"], hover=THEME["panel3"], fg=THEME["muted"], padx=18, pady=9)
            btn.pack(side="left", padx=(0, 8))
            self.tab_buttons[name] = btn

        tk.Label(wrap, text="Ctrl+R Run  •  Ctrl+S Save  •  Ctrl+L Input", bg=THEME["bg"], fg=THEME["muted"], font=("Segoe UI", 9)).pack(side="right")

    def make_page(self, name):
        page = tk.Frame(self.page_holder, bg=THEME["bg"])
        self.pages[name] = page
        return page

    def make_card(self, parent):
        return tk.Frame(parent, bg=THEME["panel"], highlightthickness=1, highlightbackground=THEME["border"], bd=0)

    def make_entry(self, parent, var=None):
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

    def make_label(self, parent, text, size=10, bold=False, muted=False, bg=None):
        return tk.Label(parent, text=text, bg=bg or THEME["panel"], fg=THEME["muted"] if muted else THEME["text"], font=("Segoe UI", size, "bold" if bold else "normal"))

    def build_console_page(self):
        page = self.make_page("Console")
        page.columnconfigure(0, weight=1)
        page.rowconfigure(1, weight=1)

        top = self.make_card(page)
        top.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 10))
        top.columnconfigure(1, weight=1)

        self.make_label(top, "Interpreter", bold=True).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))
        spy_entry = self.make_entry(top, self.spy_var)
        spy_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 10), ipady=7)

        HoverButton(top, "Browse", self.browse_spy, bg=THEME["panel3"]).grid(row=1, column=2, padx=(0, 8), pady=(0, 10))
        HoverButton(top, "Auto", self.auto_find_spy, bg=THEME["panel3"]).grid(row=1, column=3, padx=(0, 12), pady=(0, 10))

        self.make_label(top, "Script", bold=True).grid(row=2, column=0, sticky="w", padx=12, pady=(0, 4))
        script_entry = self.make_entry(top, self.script_var)
        script_entry.grid(row=3, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12), ipady=7)

        HoverButton(top, "Browse", self.browse_script, bg=THEME["panel3"]).grid(row=3, column=2, padx=(0, 8), pady=(0, 12))
        HoverButton(top, "Open in Editor", self.open_current_script_in_editor, bg=THEME["panel3"]).grid(row=3, column=3, padx=(0, 12), pady=(0, 12))

        controls = tk.Frame(top, bg=THEME["panel"])
        controls.grid(row=4, column=0, columnspan=4, sticky="ew", padx=12, pady=(0, 12))
        HoverButton(controls, "▶ Run", self.run_embedded, bg=THEME["accent_dark"], hover=THEME["accent"], fg=THEME["black"]).pack(side="left", padx=(0, 8))
        HoverButton(controls, "■ Stop", self.stop_process, bg=THEME["danger_dark"], hover=THEME["danger"]).pack(side="left", padx=(0, 8))
        HoverButton(controls, "Clear", self.clear_console, bg=THEME["panel3"]).pack(side="left", padx=(0, 8))
        HoverButton(controls, "Open Last Error", self.open_last_error, bg=THEME["panel3"]).pack(side="left", padx=(0, 8))
        HoverButton(controls, "Refresh Scripts", self.refresh_script_list, bg=THEME["panel3"]).pack(side="left")

        console_card = self.make_card(page)
        console_card.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 10))
        console_card.rowconfigure(1, weight=1)
        console_card.columnconfigure(0, weight=1)

        header = tk.Frame(console_card, bg=THEME["panel2"])
        header.grid(row=0, column=0, sticky="ew")

        tk.Label(header, text="●", bg=THEME["panel2"], fg=THEME["danger"], font=("Segoe UI", 12, "bold")).pack(side="left", padx=(10, 2), pady=5)
        tk.Label(header, text="●", bg=THEME["panel2"], fg=THEME["warning"], font=("Segoe UI", 12, "bold")).pack(side="left", padx=2)
        tk.Label(header, text="●", bg=THEME["panel2"], fg=THEME["accent"], font=("Segoe UI", 12, "bold")).pack(side="left", padx=2)
        tk.Label(header, text="Console", bg=THEME["panel2"], fg=THEME["muted"], font=("Segoe UI", 9, "bold")).pack(side="left", padx=10)

        HoverButton(header, "Copy All", self.copy_console_all, bg=THEME["panel3"], padx=10, pady=5).pack(side="right", padx=(4, 8), pady=4)
        HoverButton(header, "Copy", self.copy_console_selection, bg=THEME["panel3"], padx=10, pady=5).pack(side="right", padx=4, pady=4)

        body = tk.Frame(console_card, bg=THEME["console"])
        body.grid(row=1, column=0, sticky="nsew", padx=1, pady=(0, 1))
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)

        self.console = tk.Text(body, bg=THEME["console"], fg=THEME["text"], insertbackground=THEME["text"], relief="flat", wrap="word", font=("Cascadia Mono", 10), undo=False, state="disabled", padx=12, pady=12)
        self.console.grid(row=0, column=0, sticky="nsew")

        cscroll = AutoHideScrollbar(body, command=self.console.yview, bg=THEME["panel2"], troughcolor=THEME["console"], activebackground=THEME["accent"], relief="flat")
        cscroll.grid(row=0, column=1, sticky="ns")
        self.console.configure(yscrollcommand=cscroll.set)

        for tag, color in [("normal", THEME["text"]), ("red", THEME["danger"]), ("green", THEME["accent"]), ("yellow", THEME["warning"]), ("blue", THEME["blue"]), ("purple", THEME["purple"]), ("muted", THEME["muted"]), ("input", "#ffffff")]:
            self.console.tag_configure(tag, foreground=color)

        self.console.bind("<Control-c>", self.copy_console_selection)
        self.console.bind("<Control-C>", self.copy_console_selection)
        self.console.bind("<Control-a>", self.select_all_console)
        self.console.bind("<Control-A>", self.select_all_console)
        self.console.bind("<Button-3>", self.show_console_menu)

        self.console_menu = tk.Menu(self.console, tearoff=0, bg=THEME["panel2"], fg=THEME["text"], activebackground=THEME["accent_dark"], activeforeground=THEME["black"], relief="flat")
        self.console_menu.add_command(label="Copy selected", command=self.copy_console_selection)
        self.console_menu.add_command(label="Copy all", command=self.copy_console_all)
        self.console_menu.add_separator()
        self.console_menu.add_command(label="Clear console", command=self.clear_console)

        input_card = self.make_card(page)
        input_card.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))
        input_card.columnconfigure(0, weight=1)

        tk.Label(input_card, text="Input", bg=THEME["panel"], fg=THEME["muted"], font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 5))

        input_row = tk.Frame(input_card, bg=THEME["panel"])
        input_row.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        input_row.columnconfigure(0, weight=1)

        self.input_entry = self.make_entry(input_row, self.input_var)
        self.input_entry.configure(font=("Cascadia Mono", 11))
        self.input_entry.grid(row=0, column=0, sticky="ew", ipady=8)
        self.input_entry.bind("<Return>", self.on_input_enter)

        HoverButton(input_row, "Paste", self.paste_to_input, bg=THEME["panel3"]).grid(row=0, column=1, padx=(8, 0))
        HoverButton(input_row, "Send", self.send_input, bg=THEME["accent_dark"], hover=THEME["accent"], fg=THEME["black"]).grid(row=0, column=2, padx=(8, 0))

    def build_editor_page(self):
        page = self.make_page("Editor")
        page.rowconfigure(1, weight=1)
        page.columnconfigure(0, weight=1)

        toolbar = self.make_card(page)
        toolbar.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 10))
        toolbar.columnconfigure(1, weight=1)

        tk.Label(toolbar, text="Editor", bg=THEME["panel"], fg=THEME["text"], font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))
        tk.Label(toolbar, textvariable=self.editor_path_var, bg=THEME["panel"], fg=THEME["muted"], font=("Segoe UI", 9)).grid(row=0, column=1, sticky="w", pady=(10, 4))

        btns = tk.Frame(toolbar, bg=THEME["panel"])
        btns.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12))

        HoverButton(btns, "Open", self.open_editor_file_dialog, bg=THEME["panel3"]).pack(side="left", padx=(0, 8))
        HoverButton(btns, "Save", self.save_editor, bg=THEME["accent_dark"], hover=THEME["accent"], fg=THEME["black"]).pack(side="left", padx=(0, 8))
        HoverButton(btns, "Save As", self.save_editor_as, bg=THEME["panel3"]).pack(side="left", padx=(0, 8))
        HoverButton(btns, "Run This File", self.run_editor_file, bg=THEME["panel3"]).pack(side="left", padx=(0, 8))
        HoverButton(btns, "New File", self.new_editor_file, bg=THEME["panel3"]).pack(side="left", padx=(0, 8))
        HoverButton(btns, "Go Last Error", self.open_last_error, bg=THEME["panel3"]).pack(side="left")

        editor_card = self.make_card(page)
        editor_card.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))
        editor_card.rowconfigure(0, weight=1)
        editor_card.columnconfigure(0, weight=1)

        self.editor = tk.Text(editor_card, bg=THEME["editor"], fg=THEME["text"], insertbackground=THEME["accent"], relief="flat", wrap="none", font=("Cascadia Mono", 11), undo=True, padx=16, pady=14, tabs=("1c",))
        self.editor.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

        yscroll = AutoHideScrollbar(editor_card, command=self.editor.yview, bg=THEME["panel2"], troughcolor=THEME["editor"], activebackground=THEME["accent"], relief="flat")
        yscroll.grid(row=0, column=1, sticky="ns")
        self.editor.configure(yscrollcommand=yscroll.set)

        xscroll = AutoHideScrollbar(editor_card, orient="horizontal", command=self.editor.xview, bg=THEME["panel2"], troughcolor=THEME["editor"], activebackground=THEME["accent"], relief="flat")
        xscroll.grid(row=1, column=0, sticky="ew")
        self.editor.configure(xscrollcommand=xscroll.set)

        self.editor.tag_configure("keyword", foreground=THEME["accent"])
        self.editor.tag_configure("string", foreground=THEME["warning"])
        self.editor.tag_configure("comment", foreground=THEME["muted"])
        self.editor.tag_configure("number", foreground=THEME["blue"])
        self.editor.tag_configure("error_line", background="#3a1822")

        self.editor.bind("<KeyRelease>", self.schedule_highlight)
        self.editor.bind("<Control-s>", lambda e: self.save_editor())
        self.editor.bind("<Control-S>", lambda e: self.save_editor())

    def build_scripts_page(self):
        page = self.make_page("Scripts")
        page.rowconfigure(1, weight=1)
        page.columnconfigure(0, weight=1)

        top = self.make_card(page)
        top.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 10))
        top.columnconfigure(0, weight=1)

        tk.Label(top, text="Scripts", bg=THEME["panel"], fg=THEME["text"], font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))
        search = self.make_entry(top, self.search_var)
        search.configure(font=("Segoe UI", 10))
        search.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12), ipady=8)
        self.search_var.trace_add("write", lambda *_: self.refresh_script_list())

        HoverButton(top, "Refresh", self.refresh_script_list, bg=THEME["panel3"]).grid(row=1, column=1, padx=(0, 8), pady=(0, 12))
        HoverButton(top, "New Script", self.create_starter_file, bg=THEME["panel3"]).grid(row=1, column=2, padx=(0, 12), pady=(0, 12))

        list_card = self.make_card(page)
        list_card.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))
        list_card.rowconfigure(0, weight=1)
        list_card.columnconfigure(0, weight=1)

        self.script_canvas = tk.Canvas(list_card, bg=THEME["console"], highlightthickness=0, bd=0)
        self.script_canvas.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

        scroll = AutoHideScrollbar(list_card, command=self.script_canvas.yview, bg=THEME["panel2"], troughcolor=THEME["console"], activebackground=THEME["accent"], relief="flat")
        scroll.grid(row=0, column=1, sticky="ns")
        self.script_canvas.configure(yscrollcommand=scroll.set)

        self.script_cards_frame = tk.Frame(self.script_canvas, bg=THEME["console"])
        self.script_canvas_window = self.script_canvas.create_window((0, 0), window=self.script_cards_frame, anchor="nw")

        self.script_cards_frame.bind("<Configure>", lambda event: self.script_canvas.configure(scrollregion=self.script_canvas.bbox("all")))
        self.script_canvas.bind("<Configure>", lambda event: self.script_canvas.itemconfigure(self.script_canvas_window, width=event.width))
        self.script_canvas.bind("<MouseWheel>", self.on_script_mousewheel)
        self.script_cards_frame.bind("<MouseWheel>", self.on_script_mousewheel)

    def build_settings_page(self):
        page = self.make_page("Settings")
        page.columnconfigure(0, weight=1)

        card = self.make_card(page)
        card.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 10))
        card.columnconfigure(0, weight=1)

        tk.Label(card, text="Settings", bg=THEME["panel"], fg=THEME["text"], font=("Segoe UI", 14, "bold")).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 6))
        tk.Label(card, text="Launcher config is saved in configs/spylang_launcher_config.json", bg=THEME["panel"], fg=THEME["muted"], font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 14))

        HoverButton(card, "Open SpyLang Folder", self.open_base_folder, bg=THEME["panel3"]).grid(row=2, column=0, sticky="w", padx=14, pady=(0, 10))
        HoverButton(card, "Auto Find spy.py", self.auto_find_spy, bg=THEME["panel3"]).grid(row=3, column=0, sticky="w", padx=14, pady=(0, 10))
        HoverButton(card, "Refresh Script List", self.refresh_script_list, bg=THEME["panel3"]).grid(row=4, column=0, sticky="w", padx=14, pady=(0, 10))
        HoverButton(card, "Reset Window Size", self.reset_window_size, bg=THEME["panel3"]).grid(row=5, column=0, sticky="w", padx=14, pady=(0, 14))

        info = self.make_card(page)
        info.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))

        text = (
            "v3 launcher changes:\n\n"
            "- Normal Windows taskbar-safe window\n"
            "- Console / Editor / Scripts / Settings tabs\n"
            "- Integrated editor instead of a separate white window\n"
            "- Auto-hidden scrollbars\n"
            "- Fixed input bar\n"
            "- Better error helper\n"
        )

        tk.Label(info, text=text, bg=THEME["panel"], fg=THEME["text"], font=("Segoe UI", 10), justify="left").pack(anchor="w", padx=14, pady=14)

    def build_status_bar(self, parent):
        bar = tk.Frame(parent, bg=THEME["bg"])
        bar.pack(fill="x", padx=14, pady=(0, 10))

        self.status_dot = tk.Label(bar, text="●", bg=THEME["bg"], fg=THEME["muted"], font=("Segoe UI", 12, "bold"))
        self.status_dot.pack(side="left")

        tk.Label(bar, textvariable=self.status_var, bg=THEME["bg"], fg=THEME["muted"], font=("Segoe UI", 9)).pack(side="left", padx=(6, 0))

    def show_tab(self, name):
        for page in self.pages.values():
            page.pack_forget()

        self.pages[name].pack(fill="both", expand=True)

        for tab_name, btn in self.tab_buttons.items():
            if tab_name == name:
                btn.normal_bg = THEME["accent_dark"]
                btn.hover_bg = THEME["accent"]
                btn.configure(bg=THEME["accent_dark"], fg=THEME["black"])
            else:
                btn.normal_bg = THEME["panel"]
                btn.hover_bg = THEME["panel3"]
                btn.configure(bg=THEME["panel"], fg=THEME["muted"])

        self.active_tab = name
        self.config_data["active_tab"] = name
        self.save_current_config()

        if name == "Scripts":
            self.refresh_script_list()

    def start_drag(self, event):
        if self.is_maximized:
            return
        self.drag_x = event.x_root - self.winfo_x()
        self.drag_y = event.y_root - self.winfo_y()

    def do_drag(self, event):
        if self.is_maximized:
            return
        x = event.x_root - self.drag_x
        y = event.y_root - self.drag_y
        self.geometry(f"+{x}+{y}")

    def minimize_window(self):
        self.save_window_geometry()
        self.iconify()

    def on_map_restore(self, event=None):
        pass

    def toggle_maximize(self):
        try:
            if self.state() == "zoomed":
                self.state("normal")
            else:
                self.state("zoomed")
        except Exception:
            if not self.is_maximized:
                self.restore_geometry = self.geometry()
                self.geometry(f"{self.screen_w}x{self.screen_h}+0+0")
                self.is_maximized = True
            else:
                if self.restore_geometry:
                    self.geometry(self.restore_geometry)
                self.is_maximized = False

    def toggle_fullscreen(self, event=None):
        self.toggle_maximize()
        return "break"

    def exit_fullscreen(self, event=None):
        try:
            self.state("normal")
        except Exception:
            pass
        return "break"

    def apply_windows_dark_titlebar(self):
        # Native dark title bar attempt.
        # Keeps normal taskbar behavior. If Windows ignores it, the app still works safely.
        if os.name != "nt":
            return

        try:
            self.update_idletasks()
            hwnds = []

            try:
                hwnds.append(self.winfo_id())
            except Exception:
                pass

            try:
                parent = ctypes.windll.user32.GetParent(self.winfo_id())
                if parent:
                    hwnds.append(parent)
            except Exception:
                pass

            # Remove duplicates while preserving order.
            unique_hwnds = []
            for hwnd in hwnds:
                if hwnd and hwnd not in unique_hwnds:
                    unique_hwnds.append(hwnd)

            dwmapi = ctypes.windll.dwmapi
            value_true = ctypes.c_int(1)

            def colorref(hex_color):
                hex_color = hex_color.lstrip("#")
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                return ctypes.c_int(r | (g << 8) | (b << 16))

            caption = colorref(THEME["title"])
            border = colorref(THEME["border"])
            title_text = colorref(THEME["text"])

            for hwnd in unique_hwnds:
                for attr in (20, 19):
                    try:
                        dwmapi.DwmSetWindowAttribute(
                            ctypes.c_void_p(hwnd),
                            ctypes.c_int(attr),
                            ctypes.byref(value_true),
                            ctypes.sizeof(value_true)
                        )
                    except Exception:
                        pass

                # Windows 11 title colors.
                for attr, color in ((35, caption), (34, border), (36, title_text)):
                    try:
                        dwmapi.DwmSetWindowAttribute(
                            ctypes.c_void_p(hwnd),
                            ctypes.c_int(attr),
                            ctypes.byref(color),
                            ctypes.sizeof(color)
                        )
                    except Exception:
                        pass

        except Exception:
            pass

    def reset_window_size(self):
        win_w = clamp(1180, 820, self.screen_w - 60)
        win_h = clamp(760, 560, self.screen_h - 80)
        x = max(0, (self.screen_w - win_w) // 2)
        y = max(0, (self.screen_h - win_h) // 2)
        self.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.is_maximized = False
        self.save_window_geometry()

    def save_window_geometry(self):
        if not self.is_maximized:
            self.config_data["window_geometry"] = self.geometry()
            save_config(self.config_data)

    def safe_close(self):
        self.save_window_geometry()
        self.save_current_config()
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
            except Exception:
                pass
        self.destroy()

    def write_console(self, text, tag="normal"):
        self.console.configure(state="normal")
        self.console.insert("end", text, tag)
        self.console.see("end")
        self.console.configure(state="disabled")
        self.detect_error(text)

    def clear_console(self):
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")

    def append_ansi(self, text):
        if "\f" in text:
            parts = text.split("\f")
            for i, part in enumerate(parts):
                if i > 0:
                    self.clear_console()
                self.append_ansi(part)
            return

        i = 0
        buffer = ""

        def flush():
            nonlocal buffer
            if buffer:
                self.write_console(buffer, self.current_ansi_tag)
                buffer = ""

        while i < len(text):
            if text[i] == "\x1b":
                match = re.match(r"\x1b\[([0-9;]*)([A-Za-z])", text[i:])
                if match:
                    flush()
                    code = match.group(1)
                    end = match.group(2)
                    seq = match.group(0)

                    if end == "m":
                        codes = code.split(";") if code else ["0"]
                        if "0" in codes:
                            self.current_ansi_tag = "normal"
                        if "31" in codes:
                            self.current_ansi_tag = "red"
                        elif "32" in codes:
                            self.current_ansi_tag = "green"
                        elif "33" in codes:
                            self.current_ansi_tag = "yellow"
                        elif "34" in codes:
                            self.current_ansi_tag = "blue"
                        elif "35" in codes:
                            self.current_ansi_tag = "purple"
                    i += len(seq)
                    continue
            buffer += text[i]
            i += 1

        flush()

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
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.update()
        return "break"

    def select_all_console(self, event=None):
        self.console.configure(state="normal")
        self.console.tag_add("sel", "1.0", "end")
        self.console.configure(state="disabled")
        return "break"

    def show_console_menu(self, event):
        try:
            self.console_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.console_menu.grab_release()
        return "break"

    def focus_input(self):
        self.show_tab("Console")
        self.input_entry.focus_set()
        return "break"

    def paste_to_input(self):
        try:
            self.input_var.set(self.clipboard_get())
            self.input_entry.focus_set()
            self.input_entry.icursor("end")
        except Exception:
            pass

    def detect_error(self, text):
        file_match = re.search(r"File:\s*(.+\.spy)", text, re.IGNORECASE)
        line_match = re.search(r"(?:Line:|line)\s*(\d+)", text, re.IGNORECASE)

        if file_match:
            possible = file_match.group(1).strip()
            if Path(possible).exists():
                self.last_error_file = Path(possible)

        if line_match:
            try:
                self.last_error_line = int(line_match.group(1))
                if self.last_error_file is None and self.script_var.get():
                    self.last_error_file = Path(self.script_var.get())
            except Exception:
                pass

    def run_embedded(self):
        if self.process and self.process.poll() is None:
            messagebox.showwarning("Already running", "A script is already running.")
            return

        spy = Path(self.spy_var.get().strip())
        script = Path(self.script_var.get().strip()) if self.script_var.get().strip() else None

        if not spy.exists():
            messagebox.showerror("Missing spy.py", "Select a valid spy.py file.")
            self.show_tab("Settings")
            return

        if not script or not script.exists():
            messagebox.showerror("Missing script", "Select a valid .spy script.")
            self.show_tab("Scripts")
            return

        self.save_current_config()
        self.show_tab("Console")

        python_args = find_python_command()
        args = python_args + [str(spy), str(script)]

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["SPYLANG_LAUNCHER_CONSOLE"] = "1"
        env["PYTHONUNBUFFERED"] = "1"

        self.write_console("Running script\n", "green")
        self.write_console("Python: " + " ".join(python_args) + "\n", "muted")
        self.write_console("Interpreter: " + str(spy) + "\n", "muted")
        self.write_console("Script: " + str(script) + "\n\n", "muted")

        try:
            creationflags = 0
            startupinfo = None

            if os.name == "nt":
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0

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
            self.process = None
            self.write_console("ERROR: " + str(e) + "\n", "red")
            messagebox.showerror("Launch failed", str(e))
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
        self.update_status()

    def set_editor_file(self, path):
        self.editor_file = Path(path)
        self.editor_path_var.set(str(self.editor_file))

    def open_current_script_in_editor(self):
        if self.script_var.get().strip():
            self.open_editor_file(self.script_var.get().strip())
        else:
            self.show_tab("Editor")

    def open_editor_file_dialog(self):
        path = filedialog.askopenfilename(title="Open SpyLang file", initialdir=str(BASE_DIR), filetypes=[("SpyLang files", "*.spy"), ("All files", "*.*")])
        if path:
            self.open_editor_file(path)

    def open_editor_file(self, path, goto_line=None):
        path = Path(path)
        if not path.exists():
            messagebox.showerror("File missing", str(path))
            return
        try:
            data = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            data = path.read_text(errors="replace")

        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", data)
        self.set_editor_file(path)
        self.script_var.set(str(path))
        self.save_current_config()
        self.show_tab("Editor")
        self.highlight_editor()

        if goto_line:
            self.editor.tag_remove("error_line", "1.0", "end")
            line_index = f"{goto_line}.0"
            self.editor.tag_add("error_line", line_index, f"{goto_line}.end")
            self.editor.mark_set("insert", line_index)
            self.editor.see(line_index)

    def new_editor_file(self):
        self.editor.delete("1.0", "end")
        starter = '''# New SpyLang script

PRINT GREEN "Hello from SpyLang v3!"

MENUCREATE main
MENUADD main "Start"
MENUADD main "Exit"
MENUSHOW main choice

PRINT "Selected:"
PRINT %choice%
'''
        self.editor.insert("1.0", starter)
        self.editor_file = None
        self.editor_path_var.set("Unsaved file")
        self.show_tab("Editor")
        self.highlight_editor()

    def save_editor(self):
        if self.editor_file is None:
            return self.save_editor_as()
        try:
            self.editor_file.write_text(self.editor.get("1.0", "end-1c"), encoding="utf-8")
            self.script_var.set(str(self.editor_file))
            self.save_current_config()
            self.write_console("Saved: " + str(self.editor_file) + "\n", "green")
        except Exception as e:
            messagebox.showerror("Save failed", str(e))
        return "break"

    def save_editor_as(self):
        path = filedialog.asksaveasfilename(title="Save SpyLang file", initialdir=str(BASE_DIR), defaultextension=".spy", filetypes=[("SpyLang files", "*.spy"), ("All files", "*.*")])
        if path:
            self.set_editor_file(path)
            self.save_editor()
            self.refresh_script_list()
        return "break"

    def run_editor_file(self):
        if self.editor_file is None:
            self.save_editor_as()
        else:
            self.save_editor()
        if self.editor_file:
            self.set_script(self.editor_file)
            self.run_embedded()

    def open_last_error(self):
        if self.last_error_file and Path(self.last_error_file).exists():
            self.open_editor_file(self.last_error_file, self.last_error_line)
        elif self.script_var.get().strip() and Path(self.script_var.get().strip()).exists():
            self.open_editor_file(self.script_var.get().strip(), self.last_error_line)
        else:
            messagebox.showinfo("No error", "No saved error line yet.")

    def schedule_highlight(self, event=None):
        if self.highlight_job:
            self.after_cancel(self.highlight_job)
        self.highlight_job = self.after(120, self.highlight_editor)

    def highlight_editor(self):
        self.highlight_job = None
        text = self.editor
        text.tag_remove("keyword", "1.0", "end")
        text.tag_remove("string", "1.0", "end")
        text.tag_remove("comment", "1.0", "end")
        text.tag_remove("number", "1.0", "end")

        content = text.get("1.0", "end-1c")
        lines = content.splitlines()

        for line_no, line in enumerate(lines, start=1):
            hash_index = line.find("#")
            search_line = line
            if hash_index >= 0:
                text.tag_add("comment", f"{line_no}.{hash_index}", f"{line_no}.end")
                search_line = line[:hash_index]

            for match in re.finditer(r'"[^"]*"', search_line):
                text.tag_add("string", f"{line_no}.{match.start()}", f"{line_no}.{match.end()}")

            for match in re.finditer(r"\b\d+(?:\.\d+)?\b", search_line):
                text.tag_add("number", f"{line_no}.{match.start()}", f"{line_no}.{match.end()}")

            for match in re.finditer(r"\b[A-Za-z_][A-Za-z0-9_]*\b", search_line):
                word = match.group(0).upper()
                if word in KEYWORDS:
                    text.tag_add("keyword", f"{line_no}.{match.start()}", f"{line_no}.{match.end()}")

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
        if not hasattr(self, "script_cards_frame"):
            return

        search = self.search_var.get().lower().strip()
        for child in self.script_cards_frame.winfo_children():
            child.destroy()

        found = 0
        for path in self.get_all_scripts():
            try:
                rel = path.relative_to(BASE_DIR)
            except Exception:
                rel = path
            display = str(rel).replace("\\", "/")
            if search and search not in display.lower():
                continue
            self.add_script_card(path, display)
            found += 1

        if found == 0:
            tk.Label(self.script_cards_frame, text="No .spy files found", bg=THEME["console"], fg=THEME["muted"], font=("Segoe UI", 11, "bold")).pack(fill="x", padx=12, pady=22)

    def add_script_card(self, path, display):
        folder = str(Path(display).parent).replace("\\", "/")
        if folder == ".":
            folder = "root"
        filename = Path(display).name

        card = tk.Frame(self.script_cards_frame, bg=THEME["panel2"], highlightthickness=1, highlightbackground=THEME["border"], bd=0, cursor="hand2")
        card.pack(fill="x", padx=10, pady=(10, 0))

        inner = tk.Frame(card, bg=THEME["panel2"], cursor="hand2")
        inner.pack(fill="x", padx=12, pady=10)

        icon = tk.Label(inner, text="◆", bg=THEME["panel2"], fg=THEME["accent"], font=("Segoe UI", 14, "bold"), cursor="hand2")
        icon.pack(side="left", padx=(0, 10))

        text_box = tk.Frame(inner, bg=THEME["panel2"], cursor="hand2")
        text_box.pack(side="left", fill="x", expand=True)

        name_label = tk.Label(text_box, text=filename, bg=THEME["panel2"], fg=THEME["text"], font=("Segoe UI", 11, "bold"), anchor="w", cursor="hand2")
        name_label.pack(fill="x")

        folder_label = tk.Label(text_box, text=folder, bg=THEME["panel2"], fg=THEME["muted"], font=("Segoe UI", 9), anchor="w", cursor="hand2")
        folder_label.pack(fill="x", pady=(2, 0))

        actions = tk.Frame(inner, bg=THEME["panel2"])
        actions.pack(side="right")

        HoverButton(actions, "Edit", lambda p=path: self.open_editor_file(p), bg=THEME["panel3"], padx=9, pady=5).pack(side="left", padx=(0, 6))
        HoverButton(actions, "Run", lambda p=path: self.run_script_path(p), bg=THEME["accent_dark"], hover=THEME["accent"], fg=THEME["black"], padx=9, pady=5).pack(side="left")

        widgets = [card, inner, icon, text_box, name_label, folder_label]
        for widget in widgets:
            widget.bind("<Button-1>", lambda event, p=path: self.set_script(p))
            widget.bind("<Double-Button-1>", lambda event, p=path: self.run_script_path(p))
            widget.bind("<Enter>", lambda event, c=card, i=inner: self.hover_card(c, i, True))
            widget.bind("<Leave>", lambda event, c=card, i=inner: self.hover_card(c, i, False))
            widget.bind("<MouseWheel>", self.on_script_mousewheel)

    def hover_card(self, card, inner, active):
        bg = THEME["panel3"] if active else THEME["panel2"]
        card.configure(bg=bg)
        inner.configure(bg=bg)
        for child in inner.winfo_children():
            try:
                child.configure(bg=bg)
                for sub in child.winfo_children():
                    try:
                        sub.configure(bg=bg)
                    except Exception:
                        pass
            except Exception:
                pass

    def on_script_mousewheel(self, event):
        try:
            self.script_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass
        return "break"

    def set_script(self, path):
        path = Path(path)
        self.script_var.set(str(path))
        self.selected_script_path = path

        recent = self.config_data.get("recent_scripts", [])
        path_text = str(path)
        if path_text in recent:
            recent.remove(path_text)
        recent.insert(0, path_text)
        self.config_data["recent_scripts"] = recent[:15]
        self.save_current_config()
        self.update_status()

    def run_script_path(self, path):
        self.set_script(path)
        self.run_embedded()

    def create_starter_file(self):
        path = filedialog.asksaveasfilename(title="Create SpyLang file", initialdir=str(BASE_DIR), defaultextension=".spy", filetypes=[("SpyLang files", "*.spy"), ("All files", "*.*")])
        if not path:
            return

        starter = '''# SpyLang v3 starter

PRINT GREEN "SpyLang v3 starter"

MAPFILL 20 8 "." map
MAPBORDER map "#"
SETTILE map 1 1 "P"
DRAWMAP map

MENUCREATE main
MENUADD main "Start"
MENUADD main "Exit"
MENUSHOW main choice

PRINT "Choice:"
PRINT %choice%
'''
        try:
            Path(path).write_text(starter, encoding="utf-8")
            self.refresh_script_list()
            self.open_editor_file(path)
        except Exception as e:
            messagebox.showerror("Could not create file", str(e))

    def browse_spy(self):
        path = filedialog.askopenfilename(title="Select spy.py", initialdir=str(BASE_DIR), filetypes=[("Python files", "*.py"), ("All files", "*.*")])
        if path:
            self.spy_var.set(path)
            self.save_current_config()
            self.update_status()

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

    def browse_script(self):
        path = filedialog.askopenfilename(title="Select SpyLang script", initialdir=str(BASE_DIR), filetypes=[("SpyLang files", "*.spy"), ("All files", "*.*")])
        if path:
            self.set_script(path)

    def open_base_folder(self):
        try:
            if os.name == "nt":
                os.startfile(str(BASE_DIR))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(BASE_DIR)])
            else:
                subprocess.Popen(["xdg-open", str(BASE_DIR)])
        except Exception as e:
            messagebox.showerror("Open folder failed", str(e))

    def save_current_config(self):
        self.config_data["spy_path"] = self.spy_var.get()
        self.config_data["script_path"] = self.script_var.get()
        if self.active_tab:
            self.config_data["active_tab"] = self.active_tab
        save_config(self.config_data)

    def update_status(self):
        spy = Path(self.spy_var.get()) if self.spy_var.get() else None
        script = Path(self.script_var.get()) if self.script_var.get() else None
        running = self.process is not None and self.process.poll() is None

        parts = ["Python: " + " ".join(find_python_command())]
        parts.append("spy.py: OK" if spy and spy.exists() else "spy.py: missing")
        parts.append("script: OK" if script and script.exists() else "script: not selected")
        if running:
            parts.append("running")
            self.status_dot.configure(fg=THEME["accent"])
        else:
            self.status_dot.configure(fg=THEME["muted"])

        self.status_var.set("  |  ".join(parts))


if __name__ == "__main__":
    app = SpyLangLauncher()
    app.mainloop()
