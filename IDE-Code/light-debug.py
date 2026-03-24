"""
pydbg_gui.py - Python Debugger with GUI Window (tkinter)
Double-click to launch. Requires Python 3.6+ with tkinter (built-in).
"""

import sys
import os
import linecache
import traceback
import time
import threading
import tkinter as tk
from tkinter import filedialog, font, scrolledtext

# ── Colours ────────────────────────────────────────────────────────────────
BG       = "#0f1117"   # main background
BG2      = "#1a1d27"   # panel background
BG3      = "#22263a"   # input/toolbar background
ACCENT   = "#00d4ff"   # cyan accent
GREEN    = "#39ff85"   # success / run
YELLOW   = "#ffd166"   # warnings / step
RED      = "#ff4f5e"   # errors
GRAY     = "#4a4f6a"   # borders
FG       = "#dce3f5"   # main text
FG2      = "#7b82a8"   # dimmed text
STEP_CLR = "#ffd166"
LINE_CLR = "#00d4ff"
VAR_CLR  = "#a8ff78"
ERR_CLR  = "#ff4f5e"
SRC_CLR  = "#dce3f5"
INFO_CLR = "#7b82a8"

# ── Helpers ────────────────────────────────────────────────────────────────
def src_line(filename, lineno):
    line = linecache.getline(filename, lineno)
    return line.rstrip() if line else ""

def fmt_locals(frame):
    parts = []
    for k, v in list(frame.f_locals.items())[:10]:
        if k.startswith("__"):
            continue
        try:
            rep = repr(v)
            if len(rep) > 80:
                rep = rep[:77] + "..."
        except Exception:
            rep = "<repr-error>"
        parts.append(f"    {k} = {rep}")
    return "\n".join(parts) if parts else "    (no locals)"

def build_ns(script, args):
    sys.argv = [script] + args
    return {"__name__": "__main__", "__file__": script,
            "__builtins__": __builtins__}

# ── Main App ───────────────────────────────────────────────────────────────
class PyDbgApp:
    def __init__(self, root):
        self.root    = root
        self.script  = None
        self._stop   = threading.Event()
        self._thread = None

        root.title("pydbg — Python Debugger")
        root.configure(bg=BG)
        root.geometry("860x640")
        root.minsize(640, 480)
        root.resizable(True, True)

        self._build_ui()
        self._log(INFO_CLR, "pydbg ready.  Open a script to begin.\n")

    # ── UI Build ───────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Title bar area
        top = tk.Frame(self.root, bg=BG, pady=8)
        top.pack(fill="x", padx=16)

        tk.Label(top, text="⬡ pydbg", bg=BG, fg=ACCENT,
                 font=("Courier New", 18, "bold")).pack(side="left")
        tk.Label(top, text="lightweight python debugger", bg=BG, fg=FG2,
                 font=("Courier New", 9)).pack(side="left", padx=12, pady=4)

        # ── Toolbar
        bar = tk.Frame(self.root, bg=BG3, pady=6, padx=12)
        bar.pack(fill="x")

        btn_cfg = dict(font=("Courier New", 10, "bold"), relief="flat",
                       cursor="hand2", padx=14, pady=4, bd=0)

        self.btn_open  = tk.Button(bar, text="📂  Open",
                                   bg=BG2, fg=ACCENT,
                                   activebackground=GRAY,
                                   command=self._open_file, **btn_cfg)
        self.btn_open.pack(side="left", padx=(0,6))

        self.btn_run   = tk.Button(bar, text="▶  Run",
                                   bg=BG2, fg=GREEN,
                                   activebackground=GRAY,
                                   command=self._do_run, **btn_cfg)
        self.btn_run.pack(side="left", padx=6)

        self.btn_debug = tk.Button(bar, text="🔍  Debug",
                                   bg=BG2, fg=YELLOW,
                                   activebackground=GRAY,
                                   command=self._do_debug, **btn_cfg)
        self.btn_debug.pack(side="left", padx=6)

        self.btn_stop  = tk.Button(bar, text="■  Stop",
                                   bg=BG2, fg=RED,
                                   activebackground=GRAY,
                                   state="disabled",
                                   command=self._do_stop, **btn_cfg)
        self.btn_stop.pack(side="left", padx=6)

        self.btn_clear = tk.Button(bar, text="🗑  Clear",
                                   bg=BG2, fg=FG2,
                                   activebackground=GRAY,
                                   command=self._clear, **btn_cfg)
        self.btn_clear.pack(side="right", padx=6)

        # ── File label
        self.file_var = tk.StringVar(value="No script loaded")
        fl = tk.Frame(self.root, bg=BG2, pady=5, padx=14)
        fl.pack(fill="x")
        tk.Label(fl, text="script:", bg=BG2, fg=FG2,
                 font=("Courier New", 9)).pack(side="left")
        tk.Label(fl, textvariable=self.file_var, bg=BG2, fg=ACCENT,
                 font=("Courier New", 9, "bold")).pack(side="left", padx=6)

        # ── Status bar
        self.status_var = tk.StringVar(value="idle")
        sf = tk.Frame(self.root, bg=BG3, pady=3)
        sf.pack(side="bottom", fill="x")
        self.status_dot = tk.Label(sf, text="●", bg=BG3, fg=GRAY,
                                   font=("Courier New", 11))
        self.status_dot.pack(side="left", padx=(10,4))
        tk.Label(sf, textvariable=self.status_var, bg=BG3, fg=FG2,
                 font=("Courier New", 9)).pack(side="left")
        self.time_var = tk.StringVar(value="")
        tk.Label(sf, textvariable=self.time_var, bg=BG3, fg=FG2,
                 font=("Courier New", 9)).pack(side="right", padx=10)

        # ── Output console
        cf = tk.Frame(self.root, bg=BG, padx=12, pady=8)
        cf.pack(fill="both", expand=True)

        tk.Label(cf, text="OUTPUT", bg=BG, fg=GRAY,
                 font=("Courier New", 8, "bold")).pack(anchor="w")

        self.console = scrolledtext.ScrolledText(
            cf, bg=BG2, fg=FG, insertbackground=ACCENT,
            font=("Courier New", 10), relief="flat",
            wrap="word", state="disabled", bd=0,
            selectbackground=GRAY
        )
        self.console.pack(fill="both", expand=True, pady=(4,0))

        # Colour tags
        self.console.tag_config("step",  foreground=STEP_CLR)
        self.console.tag_config("line",  foreground=LINE_CLR)
        self.console.tag_config("var",   foreground=VAR_CLR)
        self.console.tag_config("err",   foreground=ERR_CLR)
        self.console.tag_config("info",  foreground=INFO_CLR)
        self.console.tag_config("src",   foreground=SRC_CLR)
        self.console.tag_config("green", foreground=GREEN)

    # ── Logging ────────────────────────────────────────────────────────────
    def _log(self, color_or_tag, text, tag=None):
        """Append text to console. color_or_tag can be a tag name or hex colour."""
        def _write():
            self.console.configure(state="normal")
            t = tag or color_or_tag
            self.console.insert("end", text, t)
            self.console.configure(state="disabled")
            self.console.see("end")
        self.root.after(0, _write)

    def _log_step(self, step, filename, lineno, src, locs):
        def _write():
            self.console.configure(state="normal")
            self.console.insert("end", f"step {step:>4}  ", "step")
            self.console.insert("end", f"{filename}:{lineno}\n", "line")
            self.console.insert("end", f"  {src}\n", "src")
            self.console.insert("end", f"{locs}\n\n", "var")
            self.console.configure(state="disabled")
            self.console.see("end")
        self.root.after(0, _write)

    def _clear(self):
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")

    # ── Status ─────────────────────────────────────────────────────────────
    def _set_status(self, text, color=GRAY):
        self.root.after(0, lambda: [
            self.status_var.set(text),
            self.status_dot.configure(fg=color)
        ])

    def _set_running(self, yes):
        state_on  = "normal" if yes else "disabled"
        state_off = "disabled" if yes else "normal"
        def _upd():
            self.btn_stop.configure(state=state_on)
            self.btn_run.configure(state=state_off)
            self.btn_debug.configure(state=state_off)
            self.btn_open.configure(state=state_off)
        self.root.after(0, _upd)

    # ── File open ──────────────────────────────────────────────────────────
    def _open_file(self):
        path = filedialog.askopenfilename(
            title="Select Python script",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if path:
            self.script = os.path.abspath(path)
            self.file_var.set(os.path.basename(self.script))
            self._log("info", f"Loaded: {self.script}\n")
            self._set_status("script loaded", ACCENT)

    # ── Stop ───────────────────────────────────────────────────────────────
    def _do_stop(self):
        self._stop.set()
        self._log("err", "[pydbg] stop signal sent...\n")
        self._set_status("stopping...", YELLOW)

    # ── Run ────────────────────────────────────────────────────────────────
    def _do_run(self):
        if not self._check_script():
            return
        self._stop.clear()
        self._set_running(True)
        self._set_status("running...", GREEN)
        self._log("green", f"\n▶ RUN  {os.path.basename(self.script)}\n")
        self._log("info", "─" * 50 + "\n")
        self._thread = threading.Thread(target=self._run_worker, daemon=True)
        self._thread.start()

    def _run_worker(self):
        t0 = time.perf_counter()
        ns = build_ns(self.script, [])

        # Redirect stdout/stderr to console
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = _ConsoleRedirect(self._log_output)
        try:
            with open(self.script, "r", encoding="utf-8") as fh:
                code = compile(fh.read(), self.script, "exec")
            exec(code, ns)
        except SystemExit as e:
            self._log("info", f"\n[pydbg] sys.exit({e.code})\n")
        except KeyboardInterrupt:
            self._log("info", "\n[pydbg] stopped\n")
        except Exception:
            self._log("err", "\n[pydbg] EXCEPTION:\n")
            self._log("err", traceback.format_exc())
        finally:
            sys.stdout, sys.stderr = old_out, old_err
            elapsed = time.perf_counter() - t0
            self._log("info", "─" * 50 + "\n")
            self._log("green", f"done in {elapsed:.3f}s\n")
            self._set_status(f"done  ({elapsed:.3f}s)", ACCENT)
            self._set_running(False)

    # ── Debug ──────────────────────────────────────────────────────────────
    def _do_debug(self):
        if not self._check_script():
            return
        self._stop.clear()
        self._set_running(True)
        self._set_status("debugging...", YELLOW)
        self._log("step", f"\n🔍 DEBUG  ")
        self._log("line", f"{os.path.basename(self.script)}\n")
        self._log("info", "─" * 50 + "\n")
        self._thread = threading.Thread(target=self._debug_worker, daemon=True)
        self._thread.start()

    def _debug_worker(self):
        t0   = time.perf_counter()
        step = [0]
        ns   = build_ns(self.script, [])
        script = self.script

        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = _ConsoleRedirect(self._log_output)

        def tracer(frame, event, arg):
            if self._stop.is_set():
                raise KeyboardInterrupt("pydbg-stop")
            if os.path.abspath(frame.f_code.co_filename) != script:
                return tracer
            if event == "line":
                step[0] += 1
                ln   = frame.f_lineno
                src  = src_line(script, ln)
                locs = fmt_locals(frame)
                self._log_step(step[0], os.path.basename(script), ln, src, locs)
            elif event == "exception":
                et, ev, _ = arg
                self._log("err", f"[pydbg] EXCEPTION line "
                                 f"{frame.f_lineno}: {et.__name__}: {ev}\n")
            return tracer

        sys.settrace(tracer)
        try:
            with open(script, "r", encoding="utf-8") as fh:
                code = compile(fh.read(), script, "exec")
            exec(code, ns)
        except SystemExit as e:
            self._log("info", f"\n[pydbg] sys.exit({e.code})\n")
        except KeyboardInterrupt:
            self._log("info", f"\n[pydbg] stopped at step {step[0]}\n")
        except Exception:
            self._log("err", "\n[pydbg] EXCEPTION:\n")
            self._log("err", traceback.format_exc())
        finally:
            sys.settrace(None)
            sys.stdout, sys.stderr = old_out, old_err
            elapsed = time.perf_counter() - t0
            self._log("info", "─" * 50 + "\n")
            self._log("step", f"done  steps={step[0]}  time={elapsed:.3f}s\n")
            self._set_status(f"done  {step[0]} steps  ({elapsed:.3f}s)", ACCENT)
            self._set_running(False)

    # ── Helpers ────────────────────────────────────────────────────────────
    def _log_output(self, text):
        self._log("src", text)

    def _check_script(self):
        if not self.script:
            self._log("err", "[pydbg] No script loaded — click 📂 Open first.\n")
            return False
        if not os.path.isfile(self.script):
            self._log("err", f"[pydbg] File not found: {self.script}\n")
            return False
        return True


# ── stdout redirect ────────────────────────────────────────────────────────
class _ConsoleRedirect:
    def __init__(self, write_fn):
        self._write = write_fn
        self.encoding = "utf-8"

    def write(self, text):
        if text:
            self._write(text)

    def flush(self):
        pass


# ── Entry ──────────────────────────────────────────────────────────────────
def main():
    root = tk.Tk()
    app  = PyDbgApp(root)

    # If a script was passed as argument, pre-load it
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        app.script = os.path.abspath(sys.argv[1])
        app.file_var.set(os.path.basename(app.script))
        app._set_status("script loaded", ACCENT)

    root.mainloop()


if __name__ == "__main__":
    main()