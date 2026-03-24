#!/usr/bin/env python3
"""µdbg — micro debugger  |  pure Python stdlib  |  ~150 lines"""
import tkinter as tk, sys, re, threading, traceback, keyword
from tkinter import filedialog

# ── colours ──────────────────────────────────────────────────────
E,P,F,A,R,G,Y,D = "#0f1117","#161b22","#c9d1d9","#58a6ff","#ff7b72","#3fb950","#e3b341","#8b949e"

# ── syntax patterns ──────────────────────────────────────────────
SYN = [("k","#ff7b72",r"\b("+"|".join(keyword.kwlist)+r")\b"),
       ("s","#a5d6ff",r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"[^"\n]*"|\'[^\'\n]*\''),
       ("c","#8b949e",r"#[^\n]*"),("n","#79c0ff",r"\b\d+\.?\d*\b"),
       ("b","#56d364",r"\b(print|len|range|int|str|float|list|dict|set|type|open|super)\b")]

class µdbg(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("µdbg"); self.geometry("900x600"); self.configure(bg=E)
        self.fp=None; self._bps=set(); self._run=False
        self._paused=False; self._step=False
        self._ev=threading.Event(); self._cmd=None
        self._pln=None; self._fref=None
        self._build(); self._load_sample()

    def _build(self):
        # toolbar
        tb=tk.Frame(self,bg=P,pady=2); tb.pack(fill="x")
        for txt,cmd,fg in [("▶ F5",self._go,G),("⬇ F10",self._step_,Y),
                           ("⏩ F8",self._cont,A),("■ F7",self._halt,R),
                           ("Open",self._open,D),("Save",self._save,D)]:
            tk.Button(tb,text=txt,command=cmd,bg=P,fg=fg,relief="flat",
                      font=("Consolas",10),padx=8,pady=2,
                      activebackground="#21262d",activeforeground=fg,
                      cursor="hand2").pack(side="left",padx=1)
        self._st=tk.Label(tb,text="ready",bg=P,fg=D,font=("Consolas",9))
        self._st.pack(side="right",padx=8)

        # body
        body=tk.PanedWindow(self,orient="horizontal",bg="#30363d",sashwidth=3,relief="flat")
        body.pack(fill="both",expand=True)

        # editor side
        ed=tk.Frame(body,bg=E); body.add(ed,minsize=480,stretch="always")
        self._gut=tk.Text(ed,width=5,bg=P,fg=D,font=("Consolas",12),
                          state="disabled",relief="flat",bd=0,padx=2,pady=4,
                          cursor="hand2",selectbackground=P)
        self._gut.pack(side="left",fill="y")
        self._gut.bind("<Button-1>",self._tbp)
        self._gut.tag_config("b", foreground=R, background="#2d1515")
        self._gut.tag_config("p", foreground=A, background="#0e2318")

        self._ed=tk.Text(ed,bg=E,fg=F,insertbackground=A,selectbackground="#1f3a5f",
                         font=("Consolas",12),relief="flat",bd=0,padx=8,pady=4,
                         wrap="none",undo=True)
        self._ed.pack(side="left",fill="both",expand=True)
        sb=tk.Scrollbar(ed,command=self._ys,bg=P,troughcolor=P,relief="flat",width=8)
        sb.pack(side="right",fill="y")
        self._ed.config(yscrollcommand=sb.set)
        self._ed.tag_config("p_bg",background="#0e2318")
        self._ed.tag_config("b_bg",background="#2d1515")
        for t,c,_ in SYN: self._ed.tag_config(t,foreground=c)

        # right: vars + console
        rt=tk.Frame(body,bg=P); body.add(rt,minsize=220,stretch="never")

        # vars panel
        tk.Label(rt,text="VARIABLES",bg=P,fg=D,font=("Consolas",8)).pack(anchor="w",padx=6,pady=(4,0))
        self._vbox=tk.Text(rt,bg=E,fg=F,font=("Consolas",10),relief="flat",
                           bd=0,padx=6,height=10,state="disabled")
        self._vbox.pack(fill="x",padx=4)

        # console
        tk.Frame(rt,bg="#30363d",height=1).pack(fill="x",pady=4)
        hdr=tk.Frame(rt,bg=P); hdr.pack(fill="x")
        tk.Label(hdr,text="CONSOLE",bg=P,fg=D,font=("Consolas",8)).pack(side="left",padx=6)
        tk.Button(hdr,text="clr",command=self._clr,bg=P,fg=D,
                  relief="flat",font=("Consolas",8),cursor="hand2").pack(side="right",padx=4)
        self._con=tk.Text(rt,bg=E,fg=F,font=("Consolas",10),relief="flat",
                          bd=0,padx=6,state="disabled",wrap="word")
        self._con.pack(fill="both",expand=True,padx=4,pady=(0,4))
        self._con.tag_config("e",foreground=R)
        self._con.tag_config("o",foreground=G)
        self._con.tag_config("i",foreground=A)

        # bindings
        self._ed.bind("<KeyRelease>",lambda e:(self._hl(),self._sg()))
        self._ed.bind("<Tab>",lambda e:(self._ed.insert("insert","    "),"break")[1])
        self._ed.bind("<Return>",self._ai)
        self.bind_all("<F5>", lambda e:self._go())
        self.bind_all("<F7>", lambda e:self._halt())
        self.bind_all("<F8>", lambda e:self._cont())
        self.bind_all("<F9>", lambda e:self._tbp_cur())
        self.bind_all("<F10>",lambda e:self._step_())
        self.bind_all("<Control-s>",lambda e:self._save())
        self.bind_all("<Control-o>",lambda e:self._open())

    # ── gutter ────────────────────────────────────────────────────
    def _sg(self,*_):
        self._gut.config(state="normal"); self._gut.delete("1.0","end")
        n=int(self._ed.index("end-1c").split(".")[0])
        for i in range(1,n+1):
            sym="▶" if i==self._pln else "●" if i in self._bps else " "
            self._gut.insert("end",f"{sym}{i:>3}\n")
        for l in self._bps:
            if l<=n: self._gut.tag_add("b",f"{l}.0",f"{l}.end")
        if self._pln and self._pln<=n:
            self._gut.tag_add("p",f"{self._pln}.0",f"{self._pln}.end")
        self._gut.config(state="disabled")
        self._ed.tag_remove("b_bg","1.0","end")
        for l in self._bps: self._ed.tag_add("b_bg",f"{l}.0",f"{l}.end+1c")

    def _tbp(self,e):
        l=int(self._gut.index(f"@0,{e.y}").split(".")[0])
        self._bps.discard(l) if l in self._bps else self._bps.add(l); self._sg()

    def _tbp_cur(self):
        l=int(self._ed.index("insert").split(".")[0])
        self._bps.discard(l) if l in self._bps else self._bps.add(l); self._sg()

    # ── syntax ────────────────────────────────────────────────────
    def _hl(self):
        src=self._ed.get("1.0","end-1c")
        for t,_,_ in SYN: self._ed.tag_remove(t,"1.0","end")
        for t,_,p in SYN:
            for m in re.finditer(p,src,re.M):
                self._ed.tag_add(t,f"1.0+{m.start()}c",f"1.0+{m.end()}c")

    # ── editor helpers ────────────────────────────────────────────
    def _ys(self,*a): self._ed.yview(*a); self._sg()
    def _ai(self,e):
        ln=self._ed.get("insert linestart","insert")
        ind=len(ln)-len(ln.lstrip())+(4 if ln.rstrip().endswith(":") else 0)
        self._ed.insert("insert","\n"+" "*ind); self._sg(); return "break"

    # ── log ───────────────────────────────────────────────────────
    def _log(self,msg,tag=""):
        self._con.config(state="normal")
        self._con.insert("end",msg,tag); self._con.see("end")
        self._con.config(state="disabled")
    def _logs(self,m,t=""): self.after(0,self._log,m,t)
    def _clr(self):
        self._con.config(state="normal"); self._con.delete("1.0","end")
        self._con.config(state="disabled")
    def _status(self,m,fg=D): self._st.config(text=m,fg=fg)

    # ── vars panel ────────────────────────────────────────────────
    def _show_vars(self,locs):
        self._vbox.config(state="normal"); self._vbox.delete("1.0","end")
        for k,v in locs.items():
            if k.startswith("__"): continue
            try: line=f"{k} = {repr(v)[:40]}\n"
            except: line=f"{k} = ?\n"
            self._vbox.insert("end",line)
        self._vbox.config(state="disabled")

    # ── file ──────────────────────────────────────────────────────
    def _open(self):
        p=filedialog.askopenfilename(filetypes=[("Python","*.py"),("All","*.*")])
        if not p: return
        self._ed.delete("1.0","end"); self._ed.insert("1.0",open(p).read())
        self.fp=p; self.title(f"µdbg — {p}"); self._hl(); self._sg()
    def _save(self):
        if not self.fp:
            self.fp=filedialog.asksaveasfilename(defaultextension=".py")
        if self.fp: open(self.fp,"w").write(self._ed.get("1.0","end-1c")); self._status("saved",G)

    # ── run / debug ───────────────────────────────────────────────
    def _go(self):
        if self._paused: self._cont(); return
        if self._run: self._halt()
        self._log("─"*36+"\n","i"); self._run=True
        self._paused=False; self._step=False
        self._pln=None; self._cmd=None; self._ev.clear()
        self._ed.tag_remove("p_bg","1.0","end")
        self._status("running…",Y)
        threading.Thread(target=self._exec,
            args=(self._ed.get("1.0","end-1c"),),daemon=True).start()

    def _exec(self,src):
        o,e=sys.stdout,sys.stderr
        sys.stdout=sys.stderr=type("P",(),{"write":lambda s,t:self._logs(t),"flush":lambda s:None})()
        try:
            sys.settrace(self._tr)
            exec(compile(src,self.fp or "<µdbg>","exec"),{"__name__":"__main__"})
        except SystemExit: pass
        except: self._logs(traceback.format_exc(),"e")
        finally:
            sys.settrace(None); sys.stdout,sys.stderr=o,e
            self._run=False; self._pln=None
            self.after(0,self._sg)
            self._logs("\n[done]\n","o")
            self.after(0,self._status,"done ✓",G)

    def _tr(self,frame,event,arg):
        if not self._run or event!="line": return self._tr
        fn=frame.f_code.co_filename
        if fn not in (self.fp or "<µdbg>","<µdbg>","<string>"): return self._tr
        ln=frame.f_lineno
        if ln in self._bps or self._step:
            self._step=False; self._fref=frame
            self.after(0,self._pause,ln,frame)
            self._ev.clear(); self._ev.wait()
            if self._cmd=="stop": self._run=False; return None
        return self._tr

    def _pause(self,ln,frame):
        self._paused=True; self._pln=ln
        self._ed.tag_remove("p_bg","1.0","end")
        self._ed.tag_add("p_bg",f"{ln}.0",f"{ln}.end+1c")
        self._ed.see(f"{ln}.0"); self._sg()
        self._status(f"⏸ line {ln}",A)
        self._show_vars(frame.f_locals)

    def _cont(self):
        if not self._paused: return
        self._paused=False; self._cmd="cont"
        self._ed.tag_remove("p_bg","1.0","end")
        self._pln=None; self._sg(); self._status("running…",Y); self._ev.set()

    def _step_(self):
        if not self._paused: return
        self._paused=False; self._step=True; self._cmd="step"; self._ev.set()

    def _halt(self):
        self._cmd="stop"; self._run=False; self._paused=False
        self._ev.set(); self._pln=None
        self._ed.tag_remove("p_bg","1.0","end")
        self._sg(); self._status("stopped",R)

    # ── sample ────────────────────────────────────────────────────
    def _load_sample(self):
        self._ed.insert("1.0","""\
# µdbg  |  F5 run/continue · F9 breakpoint · F10 step · F7 stop

def fib(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

for i in range(10):
    print(f"fib({i}) = {fib(i)}")
"""); self._hl(); self._sg()

if __name__=="__main__": µdbg().mainloop()