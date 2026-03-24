#!/usr/bin/env python3
"""PyDebug Mini — dark, lightweight, real debugger + watch"""
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import sys, re, threading, traceback, keyword

# ── palette ──────────────────────────────────────────────────────────────────
BG, BG2, FG = "#1e1e2e", "#181825", "#cdd6f4"
SEL, BORDER  = "#313244", "#45475a"
RED, GRN, YEL, BLUE, TEAL, PUR = "#f38ba8","#a6e3a1","#f9e2af","#89b4fa","#94e2d5","#cba6f7"
FONT, UFONT  = ("Courier New", 12), ("Segoe UI", 9)

SYNTAX = [
    ("cmt", r"#[^\n]*"),
    ("str", r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"[^"\\]*(?:\\.[^"\\]*)*"|\'[^\'\\]*(?:\\.[^\'\\]*)*\''),
    ("kw",  r"\b(?:" + "|".join(keyword.kwlist) + r")\b"),
    ("con", r"\b(?:True|False|None)\b"),
    ("num", r"\b\d+\.?\d*\b"),
    ("bi",  r"\b(?:print|len|range|int|str|float|list|dict|set|tuple|type|open|super|isinstance|enumerate|zip|map|sorted)\b"),
]

# ── redirect stdout ───────────────────────────────────────────────────────────
class _Pipe:
    def __init__(self, cb): self.cb = cb
    def write(self, s):
        if s: self.cb(s)
    def flush(self): pass

# ── IDE ───────────────────────────────────────────────────────────────────────
class IDE(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PyDebug Mini"); self.geometry("1100x700"); self.configure(bg=BG)
        self.filepath   = None
        self._bps       = set()       # {lineno}
        self._watches   = []          # [expr, ...]
        self._running   = False
        self._paused    = False
        self._step_flag = False
        self._ev        = threading.Event()
        self._cmd       = None
        self._pause_ln  = None
        self._frame_ref = None        # current frame while paused
        self._build()
        self._sample()

    # ═══════════════════════════════════════════════════════════════════════════
    def _build(self):
        # ── toolbar ──────────────────────────────────────────────────────────
        tb = tk.Frame(self, bg=BG2, pady=3); tb.pack(fill="x")
        def tbtn(txt, cmd, fg=FG):
            b = tk.Button(tb, text=txt, command=cmd, bg=BG2, fg=fg,
                          relief="flat", font=UFONT, padx=9, pady=3,
                          activebackground=SEL, activeforeground=fg, cursor="hand2")
            b.pack(side="left", padx=1); return b
        tbtn("▶ Run  F5",    self._run,   GRN)
        tbtn("🐛 Debug  F6", self._debug, BLUE)
        tk.Frame(tb, bg=BORDER, width=1).pack(side="left", fill="y", pady=4)
        tbtn("⬇ Step  F10", self._step,  TEAL)
        tbtn("⏩ Cont  F8",  self._cont,  YEL)
        tk.Frame(tb, bg=BORDER, width=1).pack(side="left", fill="y", pady=4)
        tbtn("■ Stop  F7",   self._stop,  RED)
        tk.Frame(tb, bg=BORDER, width=1).pack(side="left", fill="y", pady=4)
        tbtn("Open", self._open); tbtn("Save", self._save)
        self._stlbl = tk.Label(tb, text="Ready", bg=BG2, fg=BORDER, font=UFONT)
        self._stlbl.pack(side="right", padx=10)

        # ── main area ─────────────────────────────────────────────────────────
        main = tk.PanedWindow(self, orient="horizontal", bg=BORDER,
                              sashwidth=4, relief="flat")
        main.pack(fill="both", expand=True)

        # left: gutter + editor
        left = tk.Frame(main, bg=BG)
        self.gutter = tk.Text(left, width=6, bg=BG2, fg=BORDER, font=FONT,
                              state="disabled", relief="flat", bd=0,
                              padx=4, pady=4, cursor="hand2",
                              selectbackground=BG2, selectforeground=BORDER)
        self.gutter.pack(side="left", fill="y")
        self.gutter.bind("<Button-1>", self._toggle_bp)
        self.gutter.tag_configure("bp",    foreground=RED,  background="#3a1820")
        self.gutter.tag_configure("pause", foreground=BLUE, background="#1a2840")

        self.editor = tk.Text(left, bg=BG, fg=FG, insertbackground=BLUE,
                              selectbackground=SEL, font=FONT, undo=True,
                              relief="flat", bd=0, padx=8, pady=4,
                              wrap="none", tabs="4c")
        self.editor.pack(side="left", fill="both", expand=True)
        ysb = tk.Scrollbar(left, command=self._yscroll, bg=BG2, troughcolor=BG2, relief="flat")
        ysb.pack(side="right", fill="y")
        self.editor.configure(yscrollcommand=ysb.set)
        main.add(left, minsize=500, stretch="always")

        # right panel: notebook (Watch / Variables / Stack)
        right = tk.Frame(main, bg=BG2); main.add(right, minsize=260, stretch="never")
        nb = ttk.Notebook(right); nb.pack(fill="both", expand=True)
        self._style_notebook(nb)

        # Watch tab
        w_frame = tk.Frame(nb, bg=BG2); nb.add(w_frame, text=" Watch ")
        wp = tk.Frame(w_frame, bg=BG2); wp.pack(fill="x")
        self._watch_entry = tk.Entry(wp, bg=SEL, fg=FG, insertbackground=FG,
                                     relief="flat", font=UFONT)
        self._watch_entry.pack(side="left", fill="x", expand=True, padx=4, pady=4)
        tk.Button(wp, text="+ Add", command=self._add_watch, bg=SEL, fg=BLUE,
                  relief="flat", font=UFONT, cursor="hand2").pack(side="left", padx=2)
        tk.Button(wp, text="✕", command=self._del_watch, bg=SEL, fg=RED,
                  relief="flat", font=UFONT, cursor="hand2").pack(side="left", padx=2)
        self.watch_tree = self._tree(w_frame, ("expr","value"), ("Expression","Value"))
        self.watch_tree.column("expr",  width=110)
        self.watch_tree.column("value", width=140)

        # Variables tab
        v_frame = tk.Frame(nb, bg=BG2); nb.add(v_frame, text=" Variables ")
        self.var_tree = self._tree(v_frame, ("name","value","type"), ("Name","Value","Type"))
        self.var_tree.column("name",  width=90,  stretch=False)
        self.var_tree.column("value", width=140)
        self.var_tree.column("type",  width=70,  stretch=False)

        # Stack tab
        s_frame = tk.Frame(nb, bg=BG2); nb.add(s_frame, text=" Stack ")
        self.stk_tree = self._tree(s_frame, ("func","line"), ("Function","Line"))
        self.stk_tree.column("func", width=150)
        self.stk_tree.column("line", width=50, stretch=False)

        # ── console ───────────────────────────────────────────────────────────
        bot = tk.Frame(self, bg=BG2); bot.pack(fill="x", side="bottom")
        tk.Frame(bot, bg=BORDER, height=1).pack(fill="x")
        hdr = tk.Frame(bot, bg=BG2); hdr.pack(fill="x")
        tk.Label(hdr, text=" Console", bg=BG2, fg=BORDER, font=UFONT).pack(side="left")
        tk.Button(hdr, text="Clear", command=self._clr, bg=BG2, fg=BORDER,
                  relief="flat", font=UFONT, cursor="hand2").pack(side="right", padx=4)
        self.console = scrolledtext.ScrolledText(bot, height=8, bg=BG2, fg=FG,
                                                  font=("Courier New",11),
                                                  relief="flat", bd=0, padx=8,
                                                  state="disabled")
        self.console.pack(fill="x")
        self.console.tag_configure("err",  foreground=RED)
        self.console.tag_configure("ok",   foreground=GRN)
        self.console.tag_configure("info", foreground=BLUE)

        # syntax tags
        for tag, col in [("cmt",BORDER),("str",GRN),("kw",PUR),
                         ("con",YEL),("num",YEL),("bi",TEAL)]:
            self.editor.tag_configure(tag, foreground=col)
        self.editor.tag_configure("pause_bg", background="#1a2840")
        self.editor.tag_configure("bp_bg",    background="#3a1820")

        self.editor.bind("<KeyRelease>",      self._on_key)
        self.editor.bind("<Tab>",             lambda e: (self.editor.insert("insert","    "),"break")[1])
        self.editor.bind("<Return>",          self._indent)
        self.bind_all("<F5>",  lambda e: self._run())
        self.bind_all("<F6>",  lambda e: self._debug())
        self.bind_all("<F7>",  lambda e: self._stop())
        self.bind_all("<F8>",  lambda e: self._cont())
        self.bind_all("<F10>", lambda e: self._step())

    # ── helpers ───────────────────────────────────────────────────────────────
    def _tree(self, parent, cols, heads):
        s = ttk.Style()
        sid = f"T{id(parent)}.Treeview"
        s.configure(sid, background=BG2, foreground=FG, fieldbackground=BG2,
                    borderwidth=0, rowheight=22, font=(UFONT[0],10))
        s.map(sid, background=[("selected", SEL)], foreground=[("selected", FG)])
        s.configure(f"{sid}.Heading", background=BG2, foreground=BORDER,
                    font=(UFONT[0],9,"bold"))
        tv = ttk.Treeview(parent, columns=cols, show="headings", style=sid)
        for c, h in zip(cols, heads): tv.heading(c, text=h)
        sb = tk.Scrollbar(parent, command=tv.yview, bg=BG2, troughcolor=BG2, relief="flat")
        tv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tv.pack(fill="both", expand=True)
        return tv

    def _style_notebook(self, nb):
        s = ttk.Style()
        s.theme_use("default")
        s.configure("TNotebook",       background=BG2, borderwidth=0)
        s.configure("TNotebook.Tab",   background=BG2, foreground=BORDER,
                    padding=[10,4], font=UFONT)
        s.map("TNotebook.Tab",
              background=[("selected", SEL)],
              foreground=[("selected", FG)])
        nb.configure(style="TNotebook")

    def _yscroll(self, *a):
        self.editor.yview(*a); self._sync_gutter()

    def _on_key(self, *_):
        self._highlight(); self._sync_gutter()

    def _indent(self, e):
        ln = self.editor.get("insert linestart","insert")
        ind = len(ln) - len(ln.lstrip())
        extra = 4 if ln.rstrip().endswith(":") else 0
        self.editor.insert("insert", "\n" + " "*(ind+extra))
        self._sync_gutter(); return "break"

    def _setstatus(self, msg, fg=FG):
        self._stlbl.configure(text=msg, fg=fg)

    def _log(self, msg, tag=""):
        self.console.configure(state="normal")
        self.console.insert("end", msg, tag)
        self.console.configure(state="disabled")
        self.console.see("end")

    def _clr(self):
        self.console.configure(state="normal")
        self.console.delete("1.0","end")
        self.console.configure(state="disabled")

    def _log_s(self, msg, tag=""):
        self.after(0, lambda m=msg,t=tag: self._log(m,t))

    # ── gutter ────────────────────────────────────────────────────────────────
    def _sync_gutter(self, *_):
        self.gutter.configure(state="normal")
        self.gutter.delete("1.0","end")
        n = int(self.editor.index("end-1c").split(".")[0])
        for i in range(1, n+1):
            if i == self._pause_ln:
                self.gutter.insert("end", f"▶{i:>3} \n")
            elif i in self._bps:
                self.gutter.insert("end", f"●{i:>3} \n")
            else:
                self.gutter.insert("end", f" {i:>3} \n")
        for lno in self._bps:
            if lno <= n:
                self.gutter.tag_add("bp", f"{lno}.0", f"{lno}.end")
        if self._pause_ln and self._pause_ln <= n:
            self.gutter.tag_add("pause", f"{self._pause_ln}.0", f"{self._pause_ln}.end")
        self.gutter.configure(state="disabled")
        # also tint the editor line so it's obvious even without looking at gutter
        self.editor.tag_remove("bp_bg", "1.0", "end")
        for lno in self._bps:
            self.editor.tag_add("bp_bg", f"{lno}.0", f"{lno}.end+1c")

    def _toggle_bp(self, event):
        lno = int(self.gutter.index(f"@0,{event.y}").split(".")[0])
        self._bps.discard(lno) if lno in self._bps else self._bps.add(lno)
        self._sync_gutter()

    # ── syntax highlight ──────────────────────────────────────────────────────
    def _highlight(self):
        code = self.editor.get("1.0","end-1c")
        for tag,_ in SYNTAX: self.editor.tag_remove(tag,"1.0","end")
        for tag, pat in SYNTAX:
            for m in re.finditer(pat, code, re.MULTILINE):
                self.editor.tag_add(tag, f"1.0+{m.start()}c", f"1.0+{m.end()}c")

    # ── file ──────────────────────────────────────────────────────────────────
    def _open(self):
        p = filedialog.askopenfilename(filetypes=[("Python","*.py"),("All","*.*")])
        if not p: return
        self.editor.delete("1.0","end")
        self.editor.insert("1.0", open(p).read())
        self.filepath=p; self.title(f"PyDebug Mini — {p}")
        self._on_key()

    def _save(self):
        if not self.filepath:
            self.filepath = filedialog.asksaveasfilename(defaultextension=".py")
        if self.filepath:
            open(self.filepath,"w").write(self.editor.get("1.0","end-1c"))
            self._setstatus("Saved", GRN)

    # ── run / debug ───────────────────────────────────────────────────────────
    def _run(self):   self._start(debug=False)
    def _debug(self): self._start(debug=True)

    def _start(self, debug):
        if self._running: self._stop()
        self._log("─"*48+"\n","info")
        self._running=True; self._paused=False
        self._step_flag=False; self._pause_ln=None; self._cmd=None
        self._ev.clear()
        self.editor.tag_remove("pause_bg","1.0","end")
        threading.Thread(target=self._exec,
                         args=(self.editor.get("1.0","end-1c"), debug),
                         daemon=True).start()
        self._setstatus("Running…", YEL)

    def _exec(self, code, debug):
        o,e = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = _Pipe(self._log_s)
        try:
            g = {"__name__":"__main__"}
            if debug: sys.settrace(self._trace)
            exec(compile(code, self.filepath or "<ide>","exec"), g)
        except SystemExit: pass
        except: self._log_s(traceback.format_exc(),"err")
        finally:
            sys.settrace(None)
            sys.stdout, sys.stderr = o, e
            self._running=False; self._pause_ln=None
            self.after(0, self._sync_gutter)
            self._log_s("\n[Done]\n","ok")
            self.after(0, lambda: self._setstatus("Done ✓", GRN))

    def _trace(self, frame, event, arg):
        if not self._running: return None
        if event != "line":   return self._trace
        fname = frame.f_code.co_filename
        if fname not in (self.filepath or "<ide>","<ide>","<string>"): return self._trace
        lno = frame.f_lineno
        if lno in self._bps or self._step_flag:
            self._step_flag = False
            self._frame_ref = frame
            self.after(0, lambda l=lno, f=frame: self._on_pause(l, f))
            self._ev.clear(); self._ev.wait()
            if self._cmd == "stop": self._running=False; return None
        return self._trace

    def _on_pause(self, lno, frame):
        self._paused=True; self._pause_ln=lno
        # highlight editor line
        self.editor.tag_remove("pause_bg","1.0","end")
        self.editor.tag_add("pause_bg", f"{lno}.0", f"{lno}.end+1c")
        self.editor.see(f"{lno}.0")
        self._sync_gutter()
        self._setstatus(f"⏸  Paused — line {lno}", BLUE)
        # populate variables
        self.var_tree.delete(*self.var_tree.get_children())
        for k,v in frame.f_locals.items():
            if k.startswith("__"): continue
            try:    val=repr(v)[:60]; typ=type(v).__name__
            except: val="?"; typ="?"
            self.var_tree.insert("","end", values=(k, val, typ))
        # populate call stack
        self.stk_tree.delete(*self.stk_tree.get_children())
        f = frame
        while f:
            self.stk_tree.insert("","end",
                values=(f.f_code.co_name, f.f_lineno))
            f = f.f_back
        # evaluate watches
        self._eval_watches(frame)

    def _cont(self):
        if not self._paused: return
        self._paused=False; self._cmd="cont"
        self.editor.tag_remove("pause_bg","1.0","end")
        self._pause_ln=None; self._sync_gutter()
        self._setstatus("Running…", YEL)
        self._ev.set()

    def _step(self):
        if not self._paused: return
        self._paused=False; self._step_flag=True; self._cmd="step"
        self._ev.set()

    def _stop(self):
        self._cmd="stop"; self._running=False; self._paused=False
        self._ev.set(); self._pause_ln=None
        self.editor.tag_remove("pause_bg","1.0","end")
        self._sync_gutter(); self._setstatus("Stopped", RED)

    # ── watch ─────────────────────────────────────────────────────────────────
    def _add_watch(self):
        expr = self._watch_entry.get().strip()
        if not expr or expr in self._watches: return
        self._watches.append(expr)
        self.watch_tree.insert("","end", iid=expr, values=(expr, "—"))
        self._watch_entry.delete(0,"end")
        # evaluate immediately if paused
        if self._paused and self._frame_ref:
            self._eval_watches(self._frame_ref)

    def _del_watch(self):
        sel = self.watch_tree.selection()
        for iid in sel:
            expr = self.watch_tree.item(iid,"values")[0]
            self._watches = [w for w in self._watches if w != expr]
            self.watch_tree.delete(iid)

    def _eval_watches(self, frame):
        g = frame.f_globals; l = frame.f_locals
        for expr in self._watches:
            try:    val = repr(eval(expr, g, l))[:80]
            except Exception as ex: val = f"<{ex}>"
            self.watch_tree.item(expr, values=(expr, val))

    # ── sample ────────────────────────────────────────────────────────────────
    def _sample(self):
        self.editor.insert("1.0", """\
# Click a line number to toggle a breakpoint
# F5 Run | F6 Debug | F10 Step | F8 Continue | F7 Stop
# Add expressions to Watch tab to inspect values

def factorial(n):
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result

nums = [1, 2, 3, 4, 5, 6, 7]
for n in nums:
    f = factorial(n)
    print(f"{n}! = {f}")
""")
        self._on_key()


if __name__ == "__main__":
    IDE().mainloop()