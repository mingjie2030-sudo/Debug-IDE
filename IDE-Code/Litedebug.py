"""
LiteDebug Light  ◆  Minimal Python Debugger
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A clean, lightweight Python debugger with:
  • Warm cream + charcoal + coral aesthetic
  • Platform-native mono font (Menlo / Consolas / Courier New)
  • Canvas-drawn logo in the header
  • Python-only focus (no C++/GLSL bloat)
  • ~40% less code than the premium version

Layout:
  ┌──────────────────────────────────────────┐
  │  LOGO + toolbar                          │
  ├──────────────┬───────────────────────────┤
  │  Variables   │  Gutter │ Code Editor     │
  │  Call Stack  ├─────────────────────────  │
  │              │  Output / REPL            │
  └──────────────┴───────────────────────────┘
"""

import tkinter as tk
from tkinter import ttk, filedialog
import sys, os, bdb, threading, traceback, io, tokenize, token, code, re
import linecache

# ───────────────────────────────────────────────
#  PALETTE  — Warm Cream & Charcoal
# ───────────────────────────────────────────────
C = dict(
    bg          = "#1e1e2e",
    bg_panel    = "#181825",
    bg_bar      = "#11111b",
    bg_editor   = "#1e1e2e",
    bg_sel      = "#313244",
    bg_curline  = "#252538",
    bg_bp       = "#3a1820",
    bg_dbg      = "#1a2840",
    bg_input    = "#1e1e2e",

    fg          = "#cdd6f4",
    fg_dim      = "#6c7086",
    fg_mid      = "#a6adc8",
    fg_white    = "#cdd6f4",

    accent      = "#89b4fa",
    accent_dim  = "#1e3a5f",
    accent_glow = "#74c7ec",

    teal        = "#94e2d5",
    rose        = "#f38ba8",
    indigo      = "#cba6f7",

    border      = "#313244",
    border_vis  = "#45475a",

    bp_red      = "#f38ba8",
    arrow       = "#89b4fa",

    gutter_bg   = "#181825",
    gutter_fg   = "#45475a",

    s_kw        = "#cba6f7",
    s_bi        = "#94e2d5",
    s_fn        = "#89b4fa",
    s_var       = "#cdd6f4",
    s_str       = "#a6e3a1",
    s_num       = "#fab387",
    s_cmt       = "#6c7086",
    s_op        = "#89dceb",

    green       = "#a6e3a1",
    red         = "#f38ba8",
    cyan        = "#89dceb",
    yellow      = "#f9e2af",
    orange      = "#fab387",
)

# ── Best available mono font ──────────────────
def _mono(sz):
    if sys.platform == "win32":
        return ("Consolas", sz)
    elif sys.platform == "darwin":
        return ("Menlo", sz)
    else:
        return ("DejaVu Sans Mono", sz)

def _ui(sz, bold=False):
    w = "bold" if bold else "normal"
    if sys.platform == "win32":
        return ("Segoe UI", sz, w)
    elif sys.platform == "darwin":
        return ("SF Pro Text", sz, w)
    else:
        return ("Ubuntu", sz, w)

MONO  = _mono(12)
MONOS = _mono(10)
UI    = _ui(10)
UIB   = _ui(10, True)
UIS   = _ui(9)

# ── Python keywords / builtins ─────────────────
PY_KW = {
    'False','None','True','and','as','assert','async','await','break',
    'class','continue','def','del','elif','else','except','finally',
    'for','from','global','if','import','in','is','lambda','nonlocal',
    'not','or','pass','raise','return','try','while','with','yield'
}
PY_BI = {
    'abs','all','any','bin','bool','bytes','callable','chr','dict',
    'dir','enumerate','eval','exec','filter','float','format',
    'frozenset','getattr','globals','hasattr','hash','help','hex',
    'id','input','int','isinstance','issubclass','iter','len',
    'list','locals','map','max','min','next','object','oct','open',
    'ord','pow','print','property','range','repr','reversed','round',
    'set','setattr','slice','sorted','staticmethod','str','sum',
    'super','tuple','type','vars','zip',
    'Exception','ValueError','TypeError','KeyError','IndexError',
    'AttributeError','NotImplementedError','RuntimeError','StopIteration',
}

# ── Syntax highlighting ────────────────────────
def hl_python(widget):
    src = widget.get("1.0", "end-1c")
    for t in ("kw","bi","fn","var","str_","num","cmt","op","self_"):
        widget.tag_remove(t, "1.0", "end")
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except tokenize.TokenError:
        return
    prev = None
    for tok in toks:
        tt, ts, (sr, sc), (er, ec), _ = tok
        s, e = f"{sr}.{sc}", f"{er}.{ec}"
        if tt == token.NAME:
            if ts == "self":                           widget.tag_add("self_", s, e)
            elif ts in PY_KW:                          widget.tag_add("kw",    s, e)
            elif ts in PY_BI:                          widget.tag_add("bi",    s, e)
            elif prev and prev[1] in ("def","class"):  widget.tag_add("fn",    s, e)
            else:                                      widget.tag_add("var",   s, e)
        elif tt == token.STRING:  widget.tag_add("str_", s, e)
        elif tt == token.NUMBER:  widget.tag_add("num",  s, e)
        elif tt == token.COMMENT: widget.tag_add("cmt",  s, e)
        elif tt == token.OP:      widget.tag_add("op",   s, e)
        if tt not in (token.NEWLINE, token.NL, token.INDENT,
                      token.DEDENT, token.ENCODING, token.COMMENT,
                      token.ERRORTOKEN):
            prev = tok

def apply_syntax_tags(widget):
    widget.tag_config("kw",     foreground=C["s_kw"])
    widget.tag_config("bi",     foreground=C["s_bi"])
    widget.tag_config("fn",     foreground=C["s_fn"])
    widget.tag_config("var",    foreground=C["s_var"])
    widget.tag_config("str_",   foreground=C["s_str"])
    widget.tag_config("num",    foreground=C["s_num"])
    widget.tag_config("cmt",    foreground=C["s_cmt"], font=(*_mono(12), "italic"))
    widget.tag_config("op",     foreground=C["s_op"])
    widget.tag_config("self_",  foreground=C["s_kw"])
    widget.tag_config("curdbg", background=C["bg_dbg"])
    widget.tag_config("bp_ln",  background=C["bg_bp"])
    widget.tag_config("found",  background=C["accent_dim"])
    widget.tag_config("curline",background=C["bg_curline"])

# ── Stdout redirect ────────────────────────────
class Redirect:
    def __init__(self, cb, tag=None): self._cb = cb; self._tag = tag
    def write(self, s):
        if s: self._cb(s, self._tag)
    def flush(self): pass

# ═══════════════════════════════════════════════
#  DEBUGGER BACKEND  — all fixes applied
# ═══════════════════════════════════════════════
class Debugger(bdb.Bdb):
    def __init__(self, app):
        super().__init__()
        self.app   = app
        self._wait = threading.Event()
        self._dead = False
        self.frame = None
        # FIX 1: store the canonical filename so canonic() can match it
        self._debug_filename = None

    # FIX 1: Override canonic() so bdb doesn't mangle synthetic names like
    # "<untitled_1>" with os.path.abspath(), which breaks BP matching.
    def canonic(self, filename):
        if self._debug_filename and filename == self._debug_filename:
            return filename
        if filename.startswith('<') and filename.endswith('>'):
            return filename
        return super().canonic(filename)

    def user_line(self, frame):
        if self._dead: self.set_quit(); return
        self.frame = frame
        self.app.after(0, self.app.on_pause,
                       frame.f_code.co_filename,
                       frame.f_lineno,
                       dict(frame.f_locals),
                       self._callstack(frame))
        self._wait.clear()
        self._wait.wait()
        if self._dead: self.set_quit()

    # FIX 4: user_call and user_return were missing.
    # Without user_return the debug arrow freezes when stepping out of a function.
    def user_call(self, frame, arg):
        if self._dead: self.set_quit(); return

    def user_return(self, frame, return_value):
        if self._dead: self.set_quit(); return
        self.frame = frame
        self.app.after(0, self.app.on_pause,
                       frame.f_code.co_filename,
                       frame.f_lineno,
                       dict(frame.f_locals),
                       self._callstack(frame))
        self._wait.clear()
        self._wait.wait()
        if self._dead: self.set_quit()

    def user_exception(self, frame, exc_info):
        msg = "".join(traceback.format_exception(*exc_info))
        self.app.after(0, self.app.log, f"\n[Exception]\n{msg}\n", "err")
        self._dead = True; self.set_quit()

    def _callstack(self, frame):
        frames, f = [], frame
        while f:
            frames.append((f.f_code.co_filename, f.f_lineno, f.f_code.co_name))
            f = f.f_back
        return frames

    def cmd_continue(self): self.set_continue();         self._wait.set()
    def cmd_next(self):     self.set_next(self.frame);   self._wait.set()
    def cmd_step(self):     self.set_step();             self._wait.set()
    def cmd_return(self):   self.set_return(self.frame); self._wait.set()
    def cmd_stop(self):     self._dead = True; self.set_quit(); self._wait.set()

    # FIX 1: store filename so canonic() works correctly
    def execute(self, source, filename):
        self._dead = False
        self._debug_filename = filename
        obj = compile(source, filename, "exec")
        globs = {"__name__": "__main__", "__file__": filename}
        try:    self.run(obj, globs)
        except bdb.BdbQuit: pass
        except Exception:
            self.app.after(0, self.app.log,
                           f"\n[Error]\n{traceback.format_exc()}\n", "err")
        self.app.after(0, self.app.on_done)

# ── Default starter code ──────────────────────
DEFAULT_CODE = '''\
# LiteDebug Light  ◆  Python Debugger
# Click the gutter to set a breakpoint, then press F5.

def fibonacci(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b

def greet(name):
    message = f"Hello, {name}!"
    print(message)
    return message

names = ["Alice", "Bob", "Charlie"]
for name in names:
    greet(name)

for i in range(8):
    fib = fibonacci(i)
    print(f"fibonacci({i}) = {fib}")
'''

# FIX 2: stable per-session counter for synthetic filenames
_untitled_counter = 0

def _next_untitled():
    global _untitled_counter
    _untitled_counter += 1
    return f"<untitled_{_untitled_counter}>"

# ─────────────────────────────────────────────────────────
#  ◆ MAIN APPLICATION
# ─────────────────────────────────────────────────────────
class LiteDebugLight(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LiteDebug Dark")
        self.geometry("1180x780")
        self.minsize(800, 500)
        self.configure(bg=C["bg_panel"])

        self._file        = None
        # FIX 2: each unsaved session gets a stable synthetic debug filename
        self._debug_fname = _next_untitled()
        self._bps         = set()
        self._watches     = []
        self._dbg         = None
        self._running     = False
        self._dbg_line    = None
        self._find_win    = None
        self._repl_hist   = []
        self._repl_hidx   = -1

        self._style()
        self._build_header()
        self._build_toolbar()
        self._build_layout()
        self._build_statusbar()
        self._bind_keys()

        # FIX 5: handle window close properly
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._editor.insert("1.0", DEFAULT_CODE)
        apply_syntax_tags(self._editor)
        hl_python(self._editor)
        self._gutter_redraw()
        self._editor.focus_set()
        self._status("Ready  ◆  open a file or press F5 to run")

    # ── TTK style ─────────────────────────────────
    def _style(self):
        s = ttk.Style(self)
        s.theme_use("default")
        s.configure("D.Treeview",
            background=C["bg_panel"], foreground=C["fg"],
            fieldbackground=C["bg_panel"], borderwidth=0,
            font=MONOS, rowheight=21)
        s.configure("D.Treeview.Heading",
            background=C["bg_bar"], foreground=C["fg_mid"],
            font=UIB, borderwidth=0, relief="flat")
        s.map("D.Treeview",
            background=[("selected", C["bg_sel"])],
            foreground=[("selected", C["fg_white"])])
        s.configure("D.TNotebook",
            background=C["bg_panel"], borderwidth=0, tabmargins=[0,0,0,0])
        s.configure("D.TNotebook.Tab",
            background=C["bg_bar"], foreground=C["fg_dim"],
            padding=[14,5], font=UIB, borderwidth=0)
        s.map("D.TNotebook.Tab",
            background=[("selected", C["bg_editor"])],
            foreground=[("selected", C["accent"])],
            expand=[("selected", [0,0,0,0])])

    # ── Canvas Logo ───────────────────────────────
    def _draw_logo(self, canvas, x, y, size=22):
        s = size
        pts = [x, y-s, x+s*0.7, y, x, y+s, x-s*0.7, y]
        canvas.create_polygon(pts, fill=C["accent"], outline="", smooth=False)
        r = s * 0.28
        canvas.create_oval(x-r, y-r, x+r, y+r, fill=C["bg_editor"], outline="")
        for dx, dy in [(-s*0.8,-s*0.5),(-s*0.9,0),(-s*0.8,s*0.5),
                        (s*0.8,-s*0.5),(s*0.9,0),(s*0.8,s*0.5)]:
            canvas.create_line(x + dx*0.2, y + dy*0.15,
                               x + dx*0.7, y + dy*0.7,
                               fill=C["accent"], width=1.5, capstyle="round")

    # ── Header with logo ─────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self, bg=C["bg_bar"], height=48)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)
        tk.Frame(self, bg=C["border_vis"], height=1).pack(fill="x", side="top")

        logo_cv = tk.Canvas(hdr, width=52, height=48,
                            bg=C["bg_bar"], highlightthickness=0)
        logo_cv.pack(side="left")
        logo_cv.update_idletasks()
        self._draw_logo(logo_cv, 26, 24, size=14)

        tk.Label(hdr, text="LiteDebug", bg=C["bg_bar"],
                 fg=C["fg"], font=_ui(14, bold=True)).pack(side="left", padx=(0, 4))
        tk.Label(hdr, text="Dark", bg=C["bg_bar"],
                 fg=C["accent"], font=_ui(14)).pack(side="left")

        tk.Frame(hdr, bg=C["border_vis"], width=1).pack(
            side="left", fill="y", pady=10, padx=14)

        self._file_lbl = tk.Label(hdr, text="untitled.py",
            bg=C["bg_bar"], fg=C["fg_dim"], font=MONOS)
        self._file_lbl.pack(side="left")

        badge = tk.Frame(hdr, bg=C["accent_dim"], padx=1, pady=1)
        badge.pack(side="right", padx=14, pady=12)
        tk.Label(badge, text="  Python 3  ",
            bg=C["accent_dim"], fg=C["accent"], font=UIB,
            padx=6, pady=2).pack()

    # ── Flat button helper ────────────────────────
    def _btn(self, parent, text, cmd, fg=None, pad=(12,6)):
        b = tk.Label(parent, text=text,
            bg=C["bg_bar"], fg=fg or C["fg_mid"],
            font=UI, padx=pad[0], pady=pad[1],
            cursor="hand2", relief="flat")
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>", lambda e: b.config(bg=C["border"], fg=C["accent"]))
        b.bind("<Leave>", lambda e: b.config(bg=C["bg_bar"], fg=fg or C["fg_mid"]))
        return b

    # ── Toolbar ───────────────────────────────────
    def _build_toolbar(self):
        tb = tk.Frame(self, bg=C["bg_bar"], height=38)
        tb.pack(fill="x", side="top")
        tb.pack_propagate(False)
        tk.Frame(self, bg=C["border"], height=1).pack(fill="x", side="top")

        def vsep():
            tk.Frame(tb, bg=C["border_vis"], width=1).pack(
                side="left", fill="y", pady=6, padx=4)

        self._btn_run  = self._btn(tb, "▶  Run",      self._run,  fg=C["green"])
        self._btn_stop = self._btn(tb, "■  Stop",      self._stop, fg=C["fg_dim"])
        self._btn_run.pack(side="left")
        self._btn_stop.pack(side="left")
        vsep()
        self._btn_over = self._btn(tb, "⤵  Step Over", self._over)
        self._btn_into = self._btn(tb, "↓  Step Into", self._into)
        self._btn_out  = self._btn(tb, "↑  Step Out",  self._out)
        for b in (self._btn_over, self._btn_into, self._btn_out):
            b.pack(side="left")
        vsep()
        self._btn(tb, "⬤  Breakpoint", self._toggle_bp_cursor, fg=C["bp_red"]).pack(side="left")
        self._btn(tb, "✕  Clear BPs",  self._clear_bps).pack(side="left")
        vsep()
        self._btn(tb, "Open", self._open).pack(side="left")
        self._btn(tb, "Save", self._save).pack(side="left")
        self._btn(tb, "Find", self._find).pack(side="left")

        self._set_debug_btns(False)

    # ── Main layout ───────────────────────────────
    def _build_layout(self):
        pw = tk.PanedWindow(self, orient="horizontal",
            bg=C["border_vis"], sashwidth=4, sashrelief="flat", bd=0)
        pw.pack(fill="both", expand=True)

        left = tk.Frame(pw, bg=C["bg_panel"])
        pw.add(left, minsize=150, width=210)
        self._build_left(left)

        right = tk.PanedWindow(pw, orient="vertical",
            bg=C["border_vis"], sashwidth=4, sashrelief="flat", bd=0)
        pw.add(right, minsize=380)

        ed_fr = tk.Frame(right, bg=C["bg_editor"])
        right.add(ed_fr, minsize=180)
        self._build_editor(ed_fr)

        bot_fr = tk.Frame(right, bg=C["bg_panel"])
        right.add(bot_fr, minsize=80, height=180)
        self._build_bottom(bot_fr)

    # ── Left panel ────────────────────────────────
    def _build_left(self, parent):
        tk.Frame(parent, bg=C["border_vis"], height=1).pack(fill="x")

        self._section_header(parent, "Variables")
        self._vars = ttk.Treeview(parent,
            columns=("name","val","type"), show="headings",
            style="D.Treeview", height=9)
        for col, w, lbl in [("name",72,"Name"),("val",96,"Value"),("type",56,"Type")]:
            self._vars.heading(col, text=lbl)
            self._vars.column(col, width=w, stretch=True)
        self._vars.pack(fill="both", expand=True)

        tk.Frame(parent, bg=C["border_vis"], height=1).pack(fill="x")

        self._section_header(parent, "Call Stack")
        self._stack_tv = ttk.Treeview(parent,
            columns=("fn","file","line"), show="headings",
            style="D.Treeview", height=5)
        for col, w, lbl in [("fn",76,"Function"),("file",76,"File"),("line",38,"Ln")]:
            self._stack_tv.heading(col, text=lbl)
            self._stack_tv.column(col, width=w, stretch=True)
        self._stack_tv.pack(fill="both", expand=True)

        tk.Frame(parent, bg=C["border_vis"], height=1).pack(fill="x")

        self._section_header(parent, "Watch")
        # entry row
        wp = tk.Frame(parent, bg=C["bg_panel"]); wp.pack(fill="x", padx=4, pady=3)
        self._watch_entry = tk.Entry(wp, bg=C["bg_editor"], fg=C["fg"],
            insertbackground=C["accent"], relief="flat", font=MONOS,
            highlightthickness=1, highlightcolor=C["accent"],
            highlightbackground=C["border"])
        self._watch_entry.pack(side="left", fill="x", expand=True, ipady=3)
        self._watch_entry.bind("<Return>", lambda e: self._add_watch())
        tk.Label(wp, text=" +", bg=C["bg_panel"], fg=C["accent"],
            font=UIB, cursor="hand2").pack(side="left", padx=(3,0))
        wp.children[list(wp.children)[-1]].bind("<Button-1>", lambda e: self._add_watch())

        self.watch_tree = ttk.Treeview(parent,
            columns=("expr","value"), show="headings",
            style="D.Treeview", height=5)
        self.watch_tree.heading("expr",  text="Expression")
        self.watch_tree.heading("value", text="Value")
        self.watch_tree.column("expr",  width=90,  stretch=True)
        self.watch_tree.column("value", width=110, stretch=True)
        self.watch_tree.pack(fill="both", expand=True)
        self.watch_tree.bind("<Delete>",     lambda e: self._del_watch())
        self.watch_tree.bind("<BackSpace>",  lambda e: self._del_watch())

    def _section_header(self, parent, text):
        f = tk.Frame(parent, bg=C["bg_bar"], height=26)
        f.pack(fill="x")
        f.pack_propagate(False)
        tk.Frame(f, bg=C["accent"], width=3).pack(side="left", fill="y")
        tk.Label(f, text=f"  {text.upper()}", bg=C["bg_bar"],
                 fg=C["fg_dim"], font=UIS).pack(side="left", fill="y")

    # ── Editor ────────────────────────────────────
    def _build_editor(self, parent):
        tabbar = tk.Frame(parent, bg=C["bg_bar"], height=30)
        tabbar.pack(fill="x")
        tabbar.pack_propagate(False)

        tab = tk.Frame(tabbar, bg=C["bg_editor"])
        tab.pack(side="left", fill="y")
        self._tab_lbl = tk.Label(tab, text="  untitled.py  ",
            bg=C["bg_editor"], fg=C["fg"], font=MONOS, padx=4)
        self._tab_lbl.pack(fill="both", expand=True)
        tk.Frame(tab, bg=C["accent"], height=2).pack(fill="x")

        tk.Frame(tabbar, bg=C["bg_bar"]).pack(fill="both", expand=True)
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x")

        row = tk.Frame(parent, bg=C["bg_editor"])
        row.pack(fill="both", expand=True)

        self._gutter = tk.Canvas(row, width=48, bg=C["gutter_bg"],
            highlightthickness=0, cursor="arrow")
        self._gutter.pack(side="left", fill="y")
        self._gutter.bind("<Button-1>", self._gutter_click)

        tk.Frame(row, bg=C["border_vis"], width=1).pack(side="left", fill="y")

        ef = tk.Frame(row, bg=C["bg_editor"])
        ef.pack(fill="both", expand=True)

        self._editor = tk.Text(ef,
            bg=C["bg_editor"], fg=C["fg"],
            insertbackground=C["accent"],
            insertwidth=2,
            selectbackground=C["bg_sel"],
            selectforeground=C["fg_white"],
            font=MONO, wrap="none",
            borderwidth=0, relief="flat",
            undo=True, autoseparators=True,
            tabs=("32",), spacing1=2, spacing3=2)
        self._editor.pack(fill="both", expand=True, side="left")

        vsb = tk.Scrollbar(ef, orient="vertical", command=self._editor.yview,
                           bg=C["bg_bar"], troughcolor=C["bg_panel"], width=10,
                           activebackground=C["fg_dim"])
        vsb.pack(side="right", fill="y")
        self._editor.config(yscrollcommand=lambda *a: (vsb.set(*a), self._gutter_redraw()))

        hsb = tk.Scrollbar(parent, orient="horizontal", command=self._editor.xview,
                           bg=C["bg_bar"], troughcolor=C["bg_panel"], width=8)
        hsb.pack(fill="x")
        self._editor.config(xscrollcommand=hsb.set)

        self._editor.bind("<KeyRelease>",    self._on_key)
        self._editor.bind("<Return>",        self._auto_indent, add="+")
        self._editor.bind("<Tab>",           self._tab_key)
        self._editor.bind("<ButtonRelease>", self._update_pos)
        self._editor.bind("<MouseWheel>",    lambda e: self.after(10, self._gutter_redraw))
        self._editor.bind("<Button-4>",      lambda e: self.after(10, self._gutter_redraw))
        self._editor.bind("<Button-5>",      lambda e: self.after(10, self._gutter_redraw))

    # ── Bottom: output + REPL ─────────────────────
    def _build_bottom(self, parent):
        nb = ttk.Notebook(parent, style="D.TNotebook")
        nb.pack(fill="both", expand=True)

        out_f = tk.Frame(nb, bg=C["bg_editor"])
        nb.add(out_f, text="  Output  ")

        self._out = tk.Text(out_f, bg=C["bg_editor"], fg=C["fg"],
            font=MONOS, borderwidth=0, relief="flat",
            state="disabled", wrap="word", spacing1=1, spacing3=1)
        self._out.pack(fill="both", expand=True, side="left")
        self._out.tag_config("err",  foreground=C["rose"])
        self._out.tag_config("info", foreground=C["cyan"])
        self._out.tag_config("ok",   foreground=C["teal"])

        vsb_out = tk.Scrollbar(out_f, orient="vertical",
            command=self._out.yview,
            bg=C["bg_bar"], troughcolor=C["bg_panel"], width=10)
        vsb_out.pack(side="right", fill="y")
        self._out.config(yscrollcommand=vsb_out.set)

        repl_f = tk.Frame(nb, bg=C["bg_editor"])
        nb.add(repl_f, text="  REPL  ")
        self._build_repl(repl_f)

    def _build_repl(self, parent):
        self._repl_out = tk.Text(parent, bg=C["bg_editor"], fg=C["fg"],
            font=MONOS, borderwidth=0, relief="flat",
            state="disabled", wrap="word")
        self._repl_out.pack(fill="both", expand=True)
        self._repl_out.tag_config("err",    foreground=C["rose"])
        self._repl_out.tag_config("info",   foreground=C["teal"])
        self._repl_out.tag_config("prompt", foreground=C["accent"])

        row = tk.Frame(parent, bg=C["bg_input"])
        row.pack(fill="x")
        tk.Frame(row, bg=C["accent"], width=2).pack(side="left", fill="y")
        tk.Label(row, text="  >>>", bg=C["bg_input"],
            fg=C["accent"], font=MONOS).pack(side="left", padx=(6, 0))
        self._repl_in = tk.Entry(row, bg=C["bg_input"], fg=C["fg"],
            insertbackground=C["accent"], font=MONOS, relief="flat", borderwidth=0)
        self._repl_in.pack(fill="x", expand=True, side="left",
                           ipady=5, padx=(8, 6), pady=3)
        self._repl_in.bind("<Return>", self._repl_exec)
        self._repl_in.bind("<Up>",     self._repl_hist_up)
        self._repl_in.bind("<Down>",   self._repl_hist_down)
        self._repl_interp = code.InteractiveInterpreter()
        self._repl_write("Python REPL  ◆  type any expression\n", "info")

    # FIX 3: REPL output was broken — the fake W class didn't work because
    # InteractiveInterpreter writes to sys.stdout directly.
    # Now using Redirect class which correctly intercepts all output.
    def _repl_exec(self, e=None):
        cmd = self._repl_in.get().strip()
        if not cmd: return
        self._repl_hist.append(cmd)
        self._repl_hidx = -1
        self._repl_write(f">>> {cmd}\n", "prompt")
        self._repl_in.delete(0, "end")
        old_o, old_e = sys.stdout, sys.stderr
        sys.stdout = Redirect(lambda t, tag=None: self._repl_write(t))
        sys.stderr = Redirect(lambda t, tag=None: self._repl_write(t, "err"))
        try:
            self._repl_interp.runsource(cmd)
        except Exception:
            self._repl_write(traceback.format_exc(), "err")
        finally:
            sys.stdout, sys.stderr = old_o, old_e

    def _repl_hist_up(self, e):
        if self._repl_hist:
            self._repl_hidx = max(0, len(self._repl_hist)-1
                                  if self._repl_hidx == -1 else self._repl_hidx-1)
            self._repl_in.delete(0, "end")
            self._repl_in.insert(0, self._repl_hist[self._repl_hidx])
        return "break"

    def _repl_hist_down(self, e):
        if self._repl_hist and self._repl_hidx >= 0:
            self._repl_hidx += 1
            self._repl_in.delete(0, "end")
            if self._repl_hidx < len(self._repl_hist):
                self._repl_in.insert(0, self._repl_hist[self._repl_hidx])
            else:
                self._repl_hidx = -1
        return "break"

    def _repl_write(self, text, tag=None):
        self._repl_out.config(state="normal")
        if tag: self._repl_out.insert("end", text, tag)
        else:   self._repl_out.insert("end", text)
        self._repl_out.see("end")
        self._repl_out.config(state="disabled")

    # ── Status bar ────────────────────────────────
    def _build_statusbar(self):
        sb = tk.Frame(self, bg=C["bg_bar"], height=22)
        sb.pack(side="bottom", fill="x")
        sb.pack_propagate(False)
        tk.Frame(self, bg=C["border_vis"], height=1).pack(side="bottom", fill="x")

        tk.Frame(sb, bg=C["accent"], width=3).pack(side="left", fill="y")
        self._st_lbl = tk.Label(sb, text="  Ready",
            bg=C["bg_bar"], fg=C["fg_mid"], font=UIS, anchor="w")
        self._st_lbl.pack(side="left", fill="y", padx=4)

        self._pos_lbl = tk.Label(sb, text="Ln 1, Col 1",
            bg=C["bg_bar"], fg=C["fg_dim"], font=UIS, padx=12)
        self._pos_lbl.pack(side="right")

        tk.Frame(sb, bg=C["border_vis"], width=1).pack(
            side="right", fill="y", pady=3)

        for key, hint in [("F5","Run"), ("F9","BP"), ("F10","Over"), ("F11","Into")]:
            tk.Label(sb, text=f"  {key} ", bg=C["bg_bar"],
                fg=C["accent"], font=UIS).pack(side="right")
            tk.Label(sb, text=hint, bg=C["bg_bar"],
                fg=C["fg_dim"], font=UIS).pack(side="right")

    def _status(self, msg, bg=None):
        self._st_lbl.config(text=f"  {msg}", bg=bg or C["bg_bar"])

    # ── Keybindings ───────────────────────────────
    def _bind_keys(self):
        self.bind_all("<F5>",        lambda e: self._run())
        self.bind_all("<F9>",        lambda e: self._toggle_bp_cursor())
        self.bind_all("<F10>",       lambda e: self._over())
        self.bind_all("<F11>",       lambda e: self._into())
        self.bind_all("<Shift-F5>",  lambda e: self._stop())
        self.bind_all("<Shift-F11>", lambda e: self._out())
        self.bind_all("<Control-o>", lambda e: self._open())
        self.bind_all("<Control-s>", lambda e: self._save())
        self.bind_all("<Control-f>", lambda e: self._find())
        self.bind_all("<Control-n>", lambda e: self._new_file())

        mc = dict(bg=C["bg_panel"], fg=C["fg"],
                  activebackground=C["accent_dim"],
                  activeforeground=C["accent_glow"],
                  borderwidth=0, relief="flat", font=UI, tearoff=0)
        mb = tk.Menu(self, bg=C["bg_bar"], fg=C["fg_mid"],
                     activebackground=C["border"],
                     activeforeground=C["accent"],
                     borderwidth=0, relief="flat", font=UI)
        self.config(menu=mb)

        fm = tk.Menu(mb, **mc)
        mb.add_cascade(label="  File  ", menu=fm)
        fm.add_command(label="New File     Ctrl+N", command=self._new_file)
        fm.add_separator()
        fm.add_command(label="Open…        Ctrl+O", command=self._open)
        fm.add_command(label="Save         Ctrl+S", command=self._save)
        fm.add_command(label="Save As…",            command=self._save_as)
        fm.add_separator()
        fm.add_command(label="Exit",                command=self._on_close)

        em = tk.Menu(mb, **mc)
        mb.add_cascade(label="  Edit  ", menu=em)
        em.add_command(label="Undo   Ctrl+Z", command=lambda: self._editor.edit_undo())
        em.add_command(label="Redo   Ctrl+Y", command=lambda: self._editor.edit_redo())
        em.add_separator()
        em.add_command(label="Find   Ctrl+F", command=self._find)

        dm = tk.Menu(mb, **mc)
        mb.add_cascade(label="  Debug  ", menu=dm)
        dm.add_command(label="Run / Continue   F5",       command=self._run)
        dm.add_command(label="Stop             Shift+F5", command=self._stop)
        dm.add_separator()
        dm.add_command(label="Step Over        F10",      command=self._over)
        dm.add_command(label="Step Into        F11",      command=self._into)
        dm.add_command(label="Step Out         Shift+F11",command=self._out)
        dm.add_separator()
        dm.add_command(label="Toggle Breakpoint F9",      command=self._toggle_bp_cursor)
        dm.add_command(label="Clear All Breakpoints",     command=self._clear_bps)

    # ── Gutter ────────────────────────────────────
    def _gutter_redraw(self, e=None):
        g = self._gutter
        g.delete("all")
        i = self._editor.index("@0,0")
        while True:
            dl = self._editor.dlineinfo(i)
            if dl is None: break
            y, h = dl[1], dl[3]
            cy = y + h // 2
            ln = int(i.split(".")[0])

            if ln == self._dbg_line:
                g.create_rectangle(0, y, 48, y+h, fill=C["bg_dbg"], outline="")

            if ln in self._bps:
                g.create_oval(5, cy-5, 16, cy+5,
                    fill=C["bp_red"], outline="#FF8888", width=1)

            if ln == self._dbg_line:
                pts = [18, cy-5, 30, cy, 18, cy+5]
                g.create_polygon(pts, fill=C["arrow"], outline="", smooth=False)

            num_c = (C["accent"] if ln == self._dbg_line else
                     C["fg_mid"] if ln in self._bps else C["gutter_fg"])
            g.create_text(44, cy, text=str(ln), fill=num_c,
                          anchor="e", font=MONOS)

            nxt = self._editor.index(f"{i}+1line")
            if nxt == i: break
            i = nxt

    def _gutter_click(self, e):
        ln = int(self._editor.index(f"@0,{e.y}").split(".")[0])
        self._toggle_bp(ln)

    def _toggle_bp(self, ln):
        if ln in self._bps:
            self._bps.discard(ln)
            self._editor.tag_remove("bp_ln", f"{ln}.0", f"{ln+1}.0")
        else:
            self._bps.add(ln)
            self._editor.tag_add("bp_ln", f"{ln}.0", f"{ln+1}.0")
        self._gutter_redraw()

    def _toggle_bp_cursor(self):
        ln = int(self._editor.index("insert").split(".")[0])
        self._toggle_bp(ln)

    def _clear_bps(self):
        for ln in list(self._bps): self._toggle_bp(ln)

    # ── Editor helpers ─────────────────────────────
    def _on_key(self, e=None):
        hl_python(self._editor)
        self._gutter_redraw()
        self._update_pos()

    def _auto_indent(self, e=None):
        idx  = self._editor.index("insert")
        line = self._editor.get(f"{idx} linestart", idx)
        indent = len(line) - len(line.lstrip())
        if line.rstrip().endswith(":"): indent += 4
        self._editor.insert("insert", "\n" + " "*indent)
        return "break"

    def _tab_key(self, e=None):
        self._editor.insert("insert", "    ")
        return "break"

    def _update_pos(self, e=None):
        idx = self._editor.index("insert")
        ln, col = idx.split(".")
        try: self._pos_lbl.config(text=f"Ln {ln}, Col {int(col)+1}")
        except: pass

    # ── Lock / unlock editor during debugging ──────
    # FIX 6: prevent editing code while debugger is running
    def _lock_editor(self):
        self._editor.config(state="disabled")

    def _unlock_editor(self):
        self._editor.config(state="normal")

    # ── Run / Debug ───────────────────────────────
    def _run(self):
        if self._running:
            if self._dbg: self._dbg.cmd_continue()
            return
        src = self._editor.get("1.0", "end-1c").strip()
        if not src: return

        self._out.config(state="normal")
        self._out.delete("1.0", "end")
        self._out.config(state="disabled")

        # FIX 1+2: use stable debug filename (real path for saved files,
        # synthetic <untitled_N> for unsaved) for both compile() and set_break().
        debug_fname = os.path.abspath(self._file) if self._file else self._debug_fname

        self._dbg = Debugger(self)

        # FIX — THE CORE FIX: populate linecache so bdb.set_break() can
        # validate line numbers. Without this, set_break() silently fails
        # for any file not already on disk (including unsaved buffers and
        # freshly opened files not yet cached).
        src_lines = src.splitlines(True)
        if src_lines and not src_lines[-1].endswith('\n'):
            src_lines[-1] += '\n'
        linecache.cache[debug_fname] = (len(src), None, src_lines, debug_fname)

        if self._bps:
            for ln in sorted(self._bps):
                err = self._dbg.set_break(debug_fname, ln)
                if err:
                    self.log(f"[BP warning line {ln}]: {err}\n", "err")
                else:
                    self.log(f"[Breakpoint at line {ln}]\n", "info")
            # FIX: do NOT call set_step() when breakpoints exist —
            # it overrides them and causes pause on every line instead.
        else:
            self._dbg.set_step()

        self._running = True
        self._set_debug_btns(True)
        self._btn_run.config(text="▶  Continue")
        self._status(f"Debugging  ◆  {os.path.basename(debug_fname)}",
                     bg=C["accent_dim"])
        # FIX 6: lock editor while debugging
        self._lock_editor()

        def runner():
            old_o, old_e = sys.stdout, sys.stderr
            sys.stdout = Redirect(lambda t, tg=None: self.after(0, self.log, t, tg))
            sys.stderr = Redirect(lambda t, tg=None: self.after(0, self.log, t, "err"))
            try:    self._dbg.execute(src, debug_fname)
            finally:
                sys.stdout, sys.stderr = old_o, old_e

        threading.Thread(target=runner, daemon=True).start()

    def _stop(self):
        if self._dbg: self._dbg.cmd_stop()
        self._running  = False
        self._dbg_line = None
        self._set_debug_btns(False)
        self._btn_run.config(text="▶  Run")
        self._editor.tag_remove("curdbg", "1.0", "end")
        # FIX 6: unlock editor
        self._unlock_editor()
        self._gutter_redraw()
        self._status("Stopped")

    def _over(self):
        if self._running and self._dbg: self._dbg.cmd_next()
    def _into(self):
        if self._running and self._dbg: self._dbg.cmd_step()
    def _out(self):
        if self._running and self._dbg: self._dbg.cmd_return()

    def _set_debug_btns(self, active):
        for b in (self._btn_stop, self._btn_over, self._btn_into, self._btn_out):
            b.config(fg=C["fg"] if active else C["fg_dim"])

    # ── Debugger callbacks ────────────────────────
    def on_pause(self, fname, lineno, locs, stack):
        self._dbg_line = lineno
        self._editor.tag_remove("curdbg", "1.0", "end")
        self._editor.tag_add("curdbg", f"{lineno}.0", f"{lineno+1}.0")
        self._editor.see(f"{lineno}.0")
        self._gutter_redraw()

        for r in self._vars.get_children(): self._vars.delete(r)
        for k, v in sorted(locs.items()):
            if k.startswith("__"): continue
            try:
                t = type(v).__name__
                rv = repr(v)
                if len(rv) > 80: rv = rv[:77] + "…"
            except: t = "?"; rv = "?"
            self._vars.insert("", "end", values=(k, rv, t))

        for r in self._stack_tv.get_children(): self._stack_tv.delete(r)
        for fn, ln, name in stack:
            self._stack_tv.insert("", "end", values=(name, os.path.basename(fn), ln))

        self._status(f"Paused  ◆  Line {lineno}", bg=C["accent_dim"])
        # evaluate watch expressions
        if self._dbg and self._dbg.frame:
            self._eval_watches(self._dbg.frame)

    def on_done(self):
        self._running  = False
        self._dbg_line = None
        self._set_debug_btns(False)
        self._btn_run.config(text="▶  Run")
        self._editor.tag_remove("curdbg", "1.0", "end")
        # FIX 6: unlock editor
        self._unlock_editor()
        self._gutter_redraw()
        for r in self._vars.get_children(): self._vars.delete(r)
        for r in self._stack_tv.get_children(): self._stack_tv.delete(r)
        self._clear_watch_values()
        self._status("Finished  ✔")
        self.log("\n── Finished ✔ ──\n", "ok")

    def log(self, text, tag=None):
        self._out.config(state="normal")
        if tag: self._out.insert("end", text, tag)
        else:   self._out.insert("end", text)
        self._out.see("end")
        self._out.config(state="disabled")

    # ── File ops ──────────────────────────────────
    def _new_file(self):
        self._editor.delete("1.0", "end")
        self._editor.insert("1.0", DEFAULT_CODE)
        self._file = None
        # FIX 2: fresh synthetic debug filename for each new file
        self._debug_fname = _next_untitled()
        self._update_labels("untitled.py")
        self._clear_bps()
        apply_syntax_tags(self._editor)
        hl_python(self._editor)
        self._gutter_redraw()
        self._status("New file")

    def _open(self):
        p = filedialog.askopenfilename(
            filetypes=[("Python files","*.py"), ("All files","*.*")])
        if not p: return
        with open(p, "r", encoding="utf-8") as f: src = f.read()
        self._editor.delete("1.0", "end")
        self._editor.insert("1.0", src)
        self._file = p
        # FIX 2: real files use their absolute path as debug filename
        self._debug_fname = os.path.abspath(p)
        self._update_labels(os.path.basename(p))
        self._clear_bps()
        apply_syntax_tags(self._editor)
        hl_python(self._editor)
        self._gutter_redraw()
        self._status(f"Opened  ◆  {os.path.basename(p)}")

    def _save(self):
        if self._file:
            src = self._editor.get("1.0", "end-1c")
            with open(self._file, "w", encoding="utf-8") as f:
                f.write(src)
            # FIX 2: update debug filename to real path after save
            self._debug_fname = os.path.abspath(self._file)
            self.log(f"Saved → {self._file}\n", "info")
            self._status(f"Saved  ◆  {os.path.basename(self._file)}")
        else:
            self._save_as()

    def _save_as(self):
        p = filedialog.asksaveasfilename(defaultextension=".py",
            filetypes=[("Python","*.py"), ("All","*.*")])
        if not p: return
        self._file = p
        self._save()
        self._update_labels(os.path.basename(p))

    def _update_labels(self, name):
        self._file_lbl.config(text=name)
        self._tab_lbl.config(text=f"  {name}  ")

    # ── Find ──────────────────────────────────────
    def _find(self):
        if self._find_win and self._find_win.winfo_exists():
            self._find_win.lift(); return
        win = tk.Toplevel(self)
        win.title("Find")
        win.geometry("360x68")
        win.configure(bg=C["bg_input"])
        win.resizable(False, False)
        self._find_win = win
        tk.Frame(win, bg=C["accent"], height=2).pack(fill="x")

        row = tk.Frame(win, bg=C["bg_input"])
        row.pack(fill="x", padx=12, pady=12)
        tk.Label(row, text="Find", bg=C["bg_input"],
            fg=C["fg_dim"], font=UIB).pack(side="left")
        fe = tk.Entry(row, bg=C["bg_editor"], fg=C["fg"],
            insertbackground=C["accent"], font=MONOS,
            relief="solid", borderwidth=1, highlightthickness=0)
        fe.pack(side="left", fill="x", expand=True, padx=10, ipady=4)
        fe.focus_set()

        def do_find(ev=None):
            self._editor.tag_remove("found", "1.0", "end")
            q = fe.get()
            if not q: return
            start = "1.0"
            while True:
                pos = self._editor.search(q, start, stopindex="end")
                if not pos: break
                end = f"{pos}+{len(q)}c"
                self._editor.tag_add("found", pos, end)
                start = end
            first = self._editor.tag_ranges("found")
            if first: self._editor.see(first[0])

        fe.bind("<Return>", do_find)
        tk.Button(row, text="Find", command=do_find,
            bg=C["accent"], fg="white",
            activebackground=C["accent_glow"], activeforeground="white",
            font=UIB, relief="flat", borderwidth=0,
            padx=14, pady=3, cursor="hand2").pack(side="left")

    # ── Watch ─────────────────────────────────────
    def _add_watch(self):
        expr = self._watch_entry.get().strip()
        if not expr or expr in self._watches: return
        self._watches.append(expr)
        self.watch_tree.insert("", "end", iid=expr, values=(expr, "—"))
        self._watch_entry.delete(0, "end")
        # evaluate immediately if paused
        if self._dbg and self._dbg.frame:
            self._eval_watches(self._dbg.frame)

    def _del_watch(self):
        for iid in self.watch_tree.selection():
            expr = self.watch_tree.item(iid, "values")[0]
            self._watches = [w for w in self._watches if w != expr]
            self.watch_tree.delete(iid)

    def _eval_watches(self, frame):
        g = frame.f_globals
        l = frame.f_locals
        for expr in self._watches:
            try:    val = repr(eval(expr, g, l))[:80]
            except Exception as ex: val = f"<{ex}>"
            self.watch_tree.item(expr, values=(expr, val))

    def _clear_watch_values(self):
        for expr in self._watches:
            self.watch_tree.item(expr, values=(expr, "—"))

    # ── FIX 5: clean shutdown ─────────────────────
    def _on_close(self):
        # Stop any running debug session before closing
        if self._running and self._dbg:
            self._dbg.cmd_stop()
        self.destroy()


# ── Entry point ──────────────────────────────────
if __name__ == "__main__":
    app = LiteDebugLight()
    app.mainloop()