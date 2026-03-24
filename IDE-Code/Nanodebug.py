"""
NanoPyDebug  ◆  Pure-Python Multi-Language IDE / Debugger
══════════════════════════════════════════════════════════
Pure Python — stdlib only (tkinter, bdb, tokenize, threading…)
No pip installs. No external tools needed.

Languages:
  • Python  — full step-debugger (breakpoints, step over/into/out,
               variables panel, call stack, REPL)
  • C / C++ — full syntax highlighting (keywords, builtins, preprocessor,
               OpenGL API, strings, numbers, block & line comments)
  • GLSL    — full syntax highlighting (uniforms, built-ins, swizzle types,
               gl_Position, smoothstep, texture, etc.)

Improvements over MiniPy / LiteDebug Light:
  ✔  ~25 % less code — no duplication
  ✔  Debounced highlight (150 ms after last keystroke — no lag)
  ✔  Dark slate + amber theme
  ✔  Language auto-detected from file extension on open/save
  ✔  Language badge in header updates live
  ✔  C++ / GLSL regex highlighter (block comments, preprocessor, strings)
  ✔  Smarter auto-indent (dedent after return/pass/raise/break/continue)
  ✔  All 6 original Python debugger bug-fixes preserved
  ✔  Clean shutdown (stops debug thread before destroy)
  ✔  File menu has New Python / New C++ / New GLSL options

New in Plus edition:
  ✔  Watch expressions panel (left sidebar, evaluates on every pause)
  ✔  Find & Replace dialog (Ctrl+H)
  ✔  Toggle line comment (Ctrl+/)
  ✔  Duplicate current line (Ctrl+D)
  ✔  Go to line dialog (Ctrl+G)

Keybindings:
  F5 / Shift+F5     Run-Continue / Stop
  F9                Toggle breakpoint
  F10 / F11         Step Over / Step Into
  Shift+F11         Step Out
  Ctrl+N/O/S/F      New / Open / Save / Find
  Ctrl+H            Find & Replace
  Ctrl+G            Go to line
  Ctrl+/            Toggle comment
  Ctrl+D            Duplicate line

Layout:
  ┌──────────────────────────────────────────────┐
  │  Header  (logo · filename · language badge)  │
  │  Toolbar (Run Stop Over Into Out BP…)        │
  ├──────────────┬───────────────────────────────┤
  │  Variables   │ Gutter │ Code Editor          │
  │  ──────────  ├──────────────────────────     │
  │  Call Stack  │ Output  │  REPL               │
  └──────────────┴───────────────────────────────┘

Usage:
  python NanoPyDebug.py
  python NanoPyDebug.py myfile.py
  python NanoPyDebug.py shader.frag
"""

import tkinter as tk
from tkinter import ttk, filedialog
import sys, os, bdb, threading, traceback, io, tokenize, token, code, re, linecache

# ══════════════════════════════════════════════════════════════════
#  PALETTE  — Dark Slate + Amber
# ══════════════════════════════════════════════════════════════════
C = dict(
    bg         = "#0D1117",   # deep midnight
    bg_panel   = "#0A0E14",   # darker sidebar
    bg_bar     = "#131920",   # toolbar / header
    bg_editor  = "#0D1117",
    bg_sel     = "#1C3A5E",   # selection: deep navy blue
    bg_curline = "#111820",
    bg_bp      = "#2A0E12",   # breakpoint row: dark crimson
    bg_dbg     = "#071A12",   # debug row: dark emerald
    bg_input   = "#131920",

    fg         = "#C9D1D9",
    fg_dim     = "#3D4754",
    fg_mid     = "#7A8799",
    fg_white   = "#E6EDF3",

    accent     = "#00D9FF",   # electric cyan
    accent_dim = "#041E2A",
    accent_hi  = "#7AEEFF",

    gold       = "#FFD166",   # warm gold for run/highlights
    gold_dim   = "#2A1F05",

    green      = "#3DCC91",   # vivid emerald
    red        = "#FF4D6D",   # vivid coral-red
    teal       = "#00D9FF",
    cyan       = "#00D9FF",
    rose       = "#FF4D6D",
    orange     = "#FF9F1C",

    border     = "#1E2D3D",
    border_vis = "#162030",

    bp_red     = "#FF4D6D",
    arrow      = "#FFD166",

    gutter_bg  = "#0A0E14",
    gutter_fg  = "#2D3D4F",

    # syntax colours
    s_kw   = "#FF79C6",   # pink — keywords
    s_bi   = "#00D9FF",   # cyan — builtins
    s_fn   = "#82CFFF",   # sky blue — functions
    s_var  = "#C9D1D9",   # default — variables
    s_str  = "#3DCC91",   # emerald — strings
    s_num  = "#FFD166",   # gold — numbers
    s_cmt  = "#3D4754",   # muted — comments
    s_op   = "#7A8799",   # mid — operators
    s_self = "#FF9F1C",   # orange — self
    s_dec  = "#FF9F1C",   # orange — decorators
    s_pp   = "#FF9F1C",   # orange — preprocessor
)

# ══════════════════════════════════════════════════════════════════
#  FONTS
# ══════════════════════════════════════════════════════════════════
def _mono(sz, style=""):
    face = ("Consolas"        if sys.platform == "win32"  else
            "Menlo"           if sys.platform == "darwin" else
            "DejaVu Sans Mono")
    return (face, sz) + ((style,) if style else ())

def _ui(sz, bold=False):
    face = ("Segoe UI"    if sys.platform == "win32"  else
            "SF Pro Text" if sys.platform == "darwin" else
            "Ubuntu")
    return (face, sz, "bold" if bold else "normal")

MONO  = _mono(12)
MONOS = _mono(10)
UI    = _ui(10)
UIB   = _ui(10, True)
UIS   = _ui(9)

# ══════════════════════════════════════════════════════════════════
#  LANGUAGE DETECTION
# ══════════════════════════════════════════════════════════════════
_CPP_EXT  = {'.cpp','.cxx','.cc','.c','.h','.hpp','.hxx'}
_GLSL_EXT = {'.glsl','.vert','.frag','.geom','.comp','.tesc','.tese'}

def detect_lang(path):
    if path is None: return "python"
    ext = os.path.splitext(path)[1].lower()
    if ext in _CPP_EXT:  return "cpp"
    if ext in _GLSL_EXT: return "glsl"
    return "python"

# ══════════════════════════════════════════════════════════════════
#  PYTHON  — keyword / builtin sets
# ══════════════════════════════════════════════════════════════════
PY_KW = frozenset({
    'False','None','True','and','as','assert','async','await','break',
    'class','continue','def','del','elif','else','except','finally',
    'for','from','global','if','import','in','is','lambda','nonlocal',
    'not','or','pass','raise','return','try','while','with','yield',
})
PY_BI = frozenset({
    'abs','all','any','bin','bool','bytes','callable','chr','dict','dir',
    'enumerate','eval','exec','filter','float','format','frozenset',
    'getattr','globals','hasattr','hash','help','hex','id','input','int',
    'isinstance','issubclass','iter','len','list','locals','map','max',
    'min','next','object','oct','open','ord','pow','print','property',
    'range','repr','reversed','round','set','setattr','slice','sorted',
    'staticmethod','str','sum','super','tuple','type','vars','zip',
    'Exception','ValueError','TypeError','KeyError','IndexError',
    'AttributeError','NotImplementedError','RuntimeError','StopIteration',
})

# ══════════════════════════════════════════════════════════════════
#  C / C++  — keyword / builtin / OpenGL sets
# ══════════════════════════════════════════════════════════════════
CPP_KW = frozenset({
    'alignas','alignof','and','and_eq','asm','auto','bitand','bitor',
    'bool','break','case','catch','char','char8_t','char16_t','char32_t',
    'class','compl','concept','const','consteval','constexpr','constinit',
    'const_cast','continue','co_await','co_return','co_yield','decltype',
    'default','delete','do','double','dynamic_cast','else','enum',
    'explicit','export','extern','false','float','for','friend','goto',
    'if','inline','int','long','mutable','namespace','new','noexcept',
    'not','not_eq','nullptr','operator','or','or_eq','private','protected',
    'public','register','reinterpret_cast','requires','return','short',
    'signed','sizeof','static','static_assert','static_cast','struct',
    'switch','template','this','thread_local','throw','true','try',
    'typedef','typeid','typename','union','unsigned','using','virtual',
    'void','volatile','wchar_t','while','xor','xor_eq','override','final',
    # preprocessor identifiers (appear after the #)
    'define','include','ifdef','ifndef','endif','pragma','undef','elif',
})
CPP_BI = frozenset({
    # STL
    'std','cout','cin','cerr','endl','string','vector','map','set',
    'unordered_map','unordered_set','list','deque','queue','stack',
    'pair','tuple','array','optional','function',
    'shared_ptr','unique_ptr','weak_ptr','make_shared','make_unique',
    # C stdlib
    'printf','scanf','malloc','free','memset','memcpy','strlen',
    'size_t','ptrdiff_t',
    'int8_t','int16_t','int32_t','int64_t',
    'uint8_t','uint16_t','uint32_t','uint64_t',
    # OpenGL types
    'GLuint','GLint','GLfloat','GLdouble','GLenum','GLboolean',
    'GLsizei','GLchar','GLvoid','GLbitfield','GLclampf',
    # OpenGL draw / state functions
    'glGenVertexArrays','glBindVertexArray','glGenBuffers','glBindBuffer',
    'glBufferData','glVertexAttribPointer','glEnableVertexAttribArray',
    'glCreateShader','glShaderSource','glCompileShader','glCreateProgram',
    'glAttachShader','glLinkProgram','glUseProgram','glDeleteShader',
    'glClear','glClearColor','glEnable','glDisable','glViewport',
    'glDrawArrays','glDrawElements',
    'glUniform1f','glUniform1i','glUniform2f','glUniform3f','glUniform4f',
    'glUniformMatrix4fv','glGetUniformLocation','glGetAttribLocation',
    'glGetShaderiv','glGetShaderInfoLog','glGetProgramiv','glGetProgramInfoLog',
    # OpenGL constants
    'GL_VERTEX_SHADER','GL_FRAGMENT_SHADER','GL_GEOMETRY_SHADER',
    'GL_ARRAY_BUFFER','GL_ELEMENT_ARRAY_BUFFER',
    'GL_STATIC_DRAW','GL_DYNAMIC_DRAW',
    'GL_TRIANGLES','GL_TRIANGLE_STRIP','GL_LINES','GL_POINTS',
    'GL_COLOR_BUFFER_BIT','GL_DEPTH_BUFFER_BIT','GL_DEPTH_TEST',
    'GL_TRUE','GL_FALSE','GL_FLOAT','GL_UNSIGNED_INT','GL_COMPILE_STATUS',
    # GLFW
    'glfwInit','glfwCreateWindow','glfwMakeContextCurrent',
    'glfwWindowShouldClose','glfwSwapBuffers','glfwPollEvents',
    'glfwTerminate','glfwWindowHint','glfwGetFramebufferSize',
    'GLFW_CONTEXT_VERSION_MAJOR','GLFW_CONTEXT_VERSION_MINOR',
    'GLFW_OPENGL_PROFILE','GLFW_OPENGL_CORE_PROFILE',
    'GLFWwindow',
    # GLEW
    'glewInit','glewExperimental',
})

# ══════════════════════════════════════════════════════════════════
#  GLSL  — keyword / builtin sets
# ══════════════════════════════════════════════════════════════════
GLSL_KW = frozenset({
    'attribute','const','uniform','varying','break','continue','do',
    'for','while','if','else','in','out','inout','float','int','uint',
    'void','bool','true','false','lowp','mediump','highp','precision',
    'invariant','discard','return','struct','layout','location','binding',
    'version','core','es','extension','require','enable',
    # types
    'sampler2D','sampler3D','samplerCube','sampler2DShadow',
    'vec2','vec3','vec4','bvec2','bvec3','bvec4',
    'ivec2','ivec3','ivec4','uvec2','uvec3','uvec4',
    'mat2','mat3','mat4','mat2x3','mat3x4',
})
GLSL_BI = frozenset({
    # built-in variables
    'gl_Position','gl_FragCoord','gl_FragColor','gl_PointSize',
    'gl_VertexID','gl_InstanceID','gl_FrontFacing',
    # math
    'radians','degrees','sin','cos','tan','asin','acos','atan',
    'sinh','cosh','tanh','asinh','acosh','atanh',
    'pow','exp','log','exp2','log2','sqrt','inversesqrt',
    'abs','sign','floor','trunc','round','ceil','fract','mod',
    'min','max','clamp','mix','step','smoothstep',
    'length','distance','dot','cross','normalize','reflect','refract',
    'faceforward','matrixCompMult','transpose','inverse','determinant',
    # texture
    'texture','texture2D','textureLod','textureOffset',
    'textureProj','texelFetch','textureSize',
    # derivatives / pack
    'dFdx','dFdy','fwidth',
    'packUnorm2x16','unpackUnorm2x16',
    'floatBitsToInt','intBitsToFloat','uintBitsToFloat',
})

# ══════════════════════════════════════════════════════════════════
#  SYNTAX HIGHLIGHTERS
# ══════════════════════════════════════════════════════════════════

def _setup_py_tags(w):
    w.tag_config("kw",      foreground=C["s_kw"])
    w.tag_config("bi",      foreground=C["s_bi"])
    w.tag_config("fn",      foreground=C["s_fn"])
    w.tag_config("var",     foreground=C["s_var"])
    w.tag_config("str_",    foreground=C["s_str"])
    w.tag_config("num",     foreground=C["s_num"])
    w.tag_config("cmt",     foreground=C["s_cmt"], font=_mono(12, "italic"))
    w.tag_config("op",      foreground=C["s_op"])
    w.tag_config("self_",   foreground=C["s_self"])
    w.tag_config("dec",     foreground=C["s_dec"])
    w.tag_config("curdbg",  background=C["bg_dbg"])
    w.tag_config("bp_ln",   background=C["bg_bp"])
    w.tag_config("found",   background=C["accent_dim"])
    w.tag_config("curline", background=C["bg_curline"])

def _setup_cpp_tags(w):
    w.tag_config("kw",      foreground=C["s_kw"])
    w.tag_config("bi",      foreground=C["s_bi"])
    w.tag_config("fn",      foreground=C["s_fn"])
    w.tag_config("str_",    foreground=C["s_str"])
    w.tag_config("num",     foreground=C["s_num"])
    w.tag_config("cmt",     foreground=C["s_cmt"], font=_mono(12, "italic"))
    w.tag_config("op",      foreground=C["s_op"])
    w.tag_config("pp",      foreground=C["s_pp"])
    w.tag_config("curdbg",  background=C["bg_dbg"])
    w.tag_config("bp_ln",   background=C["bg_bp"])
    w.tag_config("found",   background=C["accent_dim"])
    w.tag_config("curline", background=C["bg_curline"])


def _hl_python(w):
    """Tokeniser-based Python highlighter."""
    src = w.get("1.0", "end-1c")
    for t in ("kw","bi","fn","var","str_","num","cmt","op","self_","dec"):
        w.tag_remove(t, "1.0", "end")
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except tokenize.TokenError:
        return
    prev = None
    for tok in toks:
        tt, ts, (sr, sc), (er, ec), _ = tok
        s, e = f"{sr}.{sc}", f"{er}.{ec}"
        if tt == token.NAME:
            if   ts == "self":                             w.tag_add("self_", s, e)
            elif ts in PY_KW:                              w.tag_add("kw",    s, e)
            elif ts in PY_BI:                              w.tag_add("bi",    s, e)
            elif prev and prev[1] in ("def", "class"):     w.tag_add("fn",    s, e)
            elif prev and prev[1] == "@":                  w.tag_add("dec",   s, e)
            else:                                          w.tag_add("var",   s, e)
        elif tt == token.STRING:  w.tag_add("str_", s, e)
        elif tt == token.NUMBER:  w.tag_add("num",  s, e)
        elif tt == token.COMMENT: w.tag_add("cmt",  s, e)
        elif tt == token.OP:      w.tag_add("op",   s, e)
        if tt not in (token.NEWLINE, token.NL, token.INDENT, token.DEDENT,
                      token.ENCODING, token.COMMENT, token.ERRORTOKEN):
            prev = tok


def _hl_cpp(w, lang="cpp"):
    """
    Regex-based highlighter for C/C++ and GLSL.
    Handles: /* block comments */, // line comments, #preprocessor,
             "strings", numbers (hex/bin/float/int), identifiers,
             function calls, operators.
    """
    kw_set = GLSL_KW if lang == "glsl" else CPP_KW
    bi_set = GLSL_BI if lang == "glsl" else CPP_BI
    src    = w.get("1.0", "end-1c")

    for t in ("kw","bi","fn","str_","num","cmt","op","pp"):
        w.tag_remove(t, "1.0", "end")

    lines    = src.split("\n")
    in_block = False   # inside /* … */ spanning lines

    for lineno, line in enumerate(lines, 1):
        n = len(line)
        i = 0

        # carry-over block comment from previous line
        if in_block:
            end = line.find("*/")
            if end == -1:
                w.tag_add("cmt", f"{lineno}.0", f"{lineno}.{n}")
                continue
            w.tag_add("cmt", f"{lineno}.0", f"{lineno}.{end+2}")
            i = end + 2
            in_block = False

        while i < n:
            ch = line[i]

            # block comment  /* … */
            if line[i:i+2] == "/*":
                end = line.find("*/", i + 2)
                if end == -1:
                    w.tag_add("cmt", f"{lineno}.{i}", f"{lineno}.{n}")
                    in_block = True
                    break
                w.tag_add("cmt", f"{lineno}.{i}", f"{lineno}.{end+2}")
                i = end + 2
                continue

            # line comment  //
            if line[i:i+2] == "//":
                w.tag_add("cmt", f"{lineno}.{i}", f"{lineno}.{n}")
                break

            # preprocessor line  (#include, #version, #define …)
            if i == 0 and line.lstrip().startswith("#"):
                offset = n - len(line.lstrip())
                w.tag_add("pp", f"{lineno}.{offset}", f"{lineno}.{offset+1}")
                for m in re.finditer(r'\b([A-Za-z_]\w*)\b', line):
                    word = m.group(1); cs, ce = m.start(), m.end()
                    if   word in kw_set: w.tag_add("kw", f"{lineno}.{cs}", f"{lineno}.{ce}")
                    elif word in bi_set: w.tag_add("bi", f"{lineno}.{cs}", f"{lineno}.{ce}")
                break

            # string / char literal
            if ch in ('"', "'"):
                q = ch; j = i + 1
                while j < n:
                    if line[j] == '\\': j += 2; continue
                    if line[j] == q:    j += 1; break
                    j += 1
                w.tag_add("str_", f"{lineno}.{i}", f"{lineno}.{j}")
                i = j
                continue

            # number  (hex / binary / float / int)
            if ch.isdigit() or (ch == '.' and i + 1 < n and line[i+1].isdigit()):
                if i == 0 or (not line[i-1].isalnum() and line[i-1] != '_'):
                    m = re.match(
                        r'(0x[0-9a-fA-F]+[uUlL]*'
                        r'|0b[01]+[uUlL]*'
                        r'|\d+\.?\d*(?:[eE][+-]?\d+)?[fFlLuU]*)',
                        line[i:])
                    if m:
                        j = i + len(m.group(0))
                        w.tag_add("num", f"{lineno}.{i}", f"{lineno}.{j}")
                        i = j
                        continue

            # identifier → keyword / builtin / function call
            m = re.match(r'[A-Za-z_]\w*', line[i:])
            if m:
                word = m.group(0); j = i + len(word)
                if   word in kw_set: w.tag_add("kw", f"{lineno}.{i}", f"{lineno}.{j}")
                elif word in bi_set: w.tag_add("bi", f"{lineno}.{i}", f"{lineno}.{j}")
                elif j < n and line[j] == '(':
                    w.tag_add("fn", f"{lineno}.{i}", f"{lineno}.{j}")
                i = j
                continue

            # operator
            if ch in '+-*/%=<>!&|^~?:;,()[]{}':
                w.tag_add("op", f"{lineno}.{i}", f"{lineno}.{i+1}")
            i += 1


def highlight(w, lang):
    """Dispatch to the correct highlighter."""
    if   lang == "python":           _hl_python(w)
    elif lang in ("cpp", "glsl"):    _hl_cpp(w, lang)


# ══════════════════════════════════════════════════════════════════
#  STDOUT REDIRECT
# ══════════════════════════════════════════════════════════════════
class Redirect:
    def __init__(self, cb, tag=None): self._cb = cb; self._tag = tag
    def write(self, s):
        if s: self._cb(s, self._tag)
    def flush(self): pass


# ══════════════════════════════════════════════════════════════════
#  DEBUGGER BACKEND  (Python only — all 6 original fixes intact)
# ══════════════════════════════════════════════════════════════════
_uid = 0
def _next_untitled():
    global _uid; _uid += 1
    return f"<untitled_{_uid}>"


class Debugger(bdb.Bdb):
    def __init__(self, app):
        super().__init__()
        self.app             = app
        self._wait           = threading.Event()
        self._dead           = False
        self.frame           = None
        self._debug_filename = None   # FIX 1

    # FIX 1 — prevent bdb mangling synthetic "<untitled_N>" filenames
    def canonic(self, filename):
        if self._debug_filename and filename == self._debug_filename:
            return filename
        if filename.startswith('<') and filename.endswith('>'):
            return filename
        return super().canonic(filename)

    # FIX 4 — both user_call AND user_return must exist
    def user_call(self, frame, arg):
        if self._dead: self.set_quit()

    def user_line(self, frame):
        if self._dead: self.set_quit(); return
        self.frame = frame
        self.app.after(0, self.app.on_pause,
                       frame.f_code.co_filename, frame.f_lineno,
                       dict(frame.f_locals), self._callstack(frame))
        self._wait.clear()
        self._wait.wait()
        if self._dead: self.set_quit()

    def user_return(self, frame, return_value):
        if self._dead: self.set_quit(); return
        self.frame = frame
        self.app.after(0, self.app.on_pause,
                       frame.f_code.co_filename, frame.f_lineno,
                       dict(frame.f_locals), self._callstack(frame))
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

    # FIX 1+2 — store debug filename; populate linecache before run
    def execute(self, source, filename):
        self._dead           = False
        self._debug_filename = filename
        obj   = compile(source, filename, "exec")
        globs = {"__name__": "__main__", "__file__": filename}
        try:    self.run(obj, globs)
        except bdb.BdbQuit: pass
        except Exception:
            self.app.after(0, self.app.log,
                           f"\n[Error]\n{traceback.format_exc()}\n", "err")
        self.app.after(0, self.app.on_done)


# ══════════════════════════════════════════════════════════════════
#  DEFAULT CODE SAMPLES
# ══════════════════════════════════════════════════════════════════
DEFAULT_PY = '''\
# NanoPyDebug  ◆  Click the gutter to set a breakpoint, then press F5.

def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

def greet(name):
    msg = f"Hello, {name}!"
    print(msg)
    return msg

names = ["Alice", "Bob", "Charlie"]
for name in names:
    greet(name)

for i in range(8):
    print(f"fib({i}) = {fibonacci(i)}")
'''

DEFAULT_CPP = '''\
// OpenGL Hello Triangle  —  C++ / OpenGL example
// (Syntax highlight only in NanoPyDebug — use g++ to compile)
#include <iostream>
#include <GL/glew.h>
#include <GLFW/glfw3.h>

const char* vertSrc = R"(
    #version 330 core
    layout(location = 0) in vec3 aPos;
    void main() {
        gl_Position = vec4(aPos, 1.0);
    }
)";

const char* fragSrc = R"(
    #version 330 core
    out vec4 FragColor;
    void main() {
        FragColor = vec4(1.0, 0.5, 0.2, 1.0);
    }
)";

GLuint compileShader(GLenum type, const char* src) {
    GLuint shader = glCreateShader(type);
    glShaderSource(shader, 1, &src, nullptr);
    glCompileShader(shader);
    GLint ok = 0;
    glGetShaderiv(shader, GL_COMPILE_STATUS, &ok);
    if (!ok) {
        char log[512];
        glGetShaderInfoLog(shader, 512, nullptr, log);
        std::cerr << "Shader error: " << log << std::endl;
    }
    return shader;
}

int main() {
    glfwInit();
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

    GLFWwindow* window = glfwCreateWindow(800, 600, "Hello Triangle",
                                          nullptr, nullptr);
    if (!window) {
        std::cerr << "GLFW window failed" << std::endl;
        glfwTerminate(); return -1;
    }
    glfwMakeContextCurrent(window);
    glewExperimental = GL_TRUE;
    glewInit();

    float vertices[] = {
        -0.5f, -0.5f, 0.0f,
         0.5f, -0.5f, 0.0f,
         0.0f,  0.5f, 0.0f
    };
    GLuint VAO, VBO;
    glGenVertexArrays(1, &VAO); glBindVertexArray(VAO);
    glGenBuffers(1, &VBO);      glBindBuffer(GL_ARRAY_BUFFER, VBO);
    glBufferData(GL_ARRAY_BUFFER, sizeof(vertices), vertices, GL_STATIC_DRAW);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE,
                          3 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);

    GLuint vs   = compileShader(GL_VERTEX_SHADER,   vertSrc);
    GLuint fs   = compileShader(GL_FRAGMENT_SHADER, fragSrc);
    GLuint prog = glCreateProgram();
    glAttachShader(prog, vs); glAttachShader(prog, fs);
    glLinkProgram(prog);
    glDeleteShader(vs); glDeleteShader(fs);

    while (!glfwWindowShouldClose(window)) {
        glClearColor(0.1f, 0.1f, 0.15f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);
        glUseProgram(prog);
        glBindVertexArray(VAO);
        glDrawArrays(GL_TRIANGLES, 0, 3);
        glfwSwapBuffers(window);
        glfwPollEvents();
    }
    glfwTerminate();
    return 0;
}
'''

DEFAULT_GLSL = '''\
// GLSL Fragment Shader  ◆  syntax-highlight in NanoPyDebug
#version 330 core

in  vec2 TexCoord;
out vec4 FragColor;

uniform sampler2D uTexture;
uniform float     uTime;
uniform vec2      uResolution;

float circleSDF(vec2 p, float r) {
    return length(p) - r;
}

void main() {
    vec2  uv   = (TexCoord * 2.0 - 1.0)
                 * vec2(uResolution.x / uResolution.y, 1.0);
    float d    = circleSDF(uv, 0.5 + 0.1 * sin(uTime));
    float ring = smoothstep(0.02, 0.0, abs(d));
    vec3  col  = mix(vec3(0.1, 0.1, 0.2), vec3(0.0, 0.8, 1.0), ring);
    FragColor  = vec4(col, 1.0);
}
'''


# ══════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════════════════════════
class NanoPyDebug(tk.Tk):

    def __init__(self, filepath=None):
        super().__init__()
        self.title("NanoPyDebug Plus")
        self.geometry("1220x800")
        self.minsize(900, 550)
        self.configure(bg=C["bg_panel"])

        self._file        = None
        self._lang        = "python"
        self._debug_fname = _next_untitled()   # FIX 2
        self._bps         = set()
        self._watches     = []
        self._dbg         = None
        self._running     = False
        self._dbg_line    = None
        self._find_win    = None
        self._find_replace_win = None
        self._hl_job      = None   # debounce handle
        self._repl_hist   = []
        self._repl_hidx   = -1

        self._init_style()
        self._build_header()
        self._build_toolbar()
        self._build_layout()
        self._build_statusbar()
        self._bind_keys()
        self.protocol("WM_DELETE_WINDOW", self._on_close)   # FIX 5

        if filepath and os.path.isfile(filepath):
            self.after(80, lambda: self._open(filepath))
        else:
            self._editor.insert("1.0", DEFAULT_PY)
            _setup_py_tags(self._editor)
            _hl_python(self._editor)
            self._gutter_redraw()

        self._editor.focus_set()
        self._status("Ready  ◆  F5 run · F9 breakpoint · F10 over · F11 into")

    # ── TTK style ──────────────────────────────────────────────────
    def _init_style(self):
        s = ttk.Style(self)
        s.theme_use("default")
        s.configure("D.Treeview",
            background=C["bg_panel"], foreground=C["fg"],
            fieldbackground=C["bg_panel"], borderwidth=0,
            font=MONOS, rowheight=22)
        s.configure("D.Treeview.Heading",
            background=C["bg_bar"], foreground=C["accent"],
            font=UIB, borderwidth=0, relief="flat")
        s.map("D.Treeview",
            background=[("selected", C["bg_sel"])],
            foreground=[("selected", C["fg_white"])])
        s.configure("D.TNotebook",
            background=C["bg_panel"], borderwidth=0, tabmargins=[0,0,0,0])
        s.configure("D.TNotebook.Tab",
            background=C["bg_bar"], foreground=C["fg_dim"],
            padding=[16, 5], font=UIB, borderwidth=0)
        s.map("D.TNotebook.Tab",
            background=[("selected", C["bg_editor"])],
            foreground=[("selected", C["accent"])],
            expand=[("selected", [0, 0, 0, 0])])

    # ── Header ─────────────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self, bg=C["bg_bar"], height=48)
        hdr.pack(fill="x", side="top"); hdr.pack_propagate(False)
        tk.Frame(self, bg=C["accent"], height=1).pack(fill="x", side="top")

        # Canvas logo: hexagon with inner dot
        cv = tk.Canvas(hdr, width=48, height=48, bg=C["bg_bar"],
                       highlightthickness=0)
        cv.pack(side="left", padx=(8, 0))
        cv.update_idletasks()
        self._draw_logo(cv, 24, 24, 14)

        # Title
        tk.Label(hdr, text="Nano", bg=C["bg_bar"],
                 fg=C["fg_white"], font=_ui(15, bold=True)).pack(side="left", padx=(2, 0))
        tk.Label(hdr, text="PyDebug", bg=C["bg_bar"],
                 fg=C["accent"], font=_ui(15, bold=True)).pack(side="left")
        tk.Label(hdr, text=" Plus", bg=C["bg_bar"],
                 fg=C["fg_mid"], font=_ui(10)).pack(side="left", padx=(2, 12))

        # Separator
        tk.Frame(hdr, bg=C["border"], width=1).pack(
            side="left", fill="y", pady=10, padx=6)

        # File label
        self._file_lbl = tk.Label(hdr, text="untitled.py",
            bg=C["bg_bar"], fg=C["fg_mid"], font=MONOS, padx=6)
        self._file_lbl.pack(side="left")

        # Language badge — pill shape via padx/pady
        self._lang_badge = tk.Label(hdr, text="  🐍 Python  ",
            bg=C["accent_dim"], fg=C["accent"], font=UIB,
            padx=8, pady=3, relief="flat")
        self._lang_badge.pack(side="right", padx=12, pady=10)

    def _draw_logo(self, canvas, cx, cy, r):
        """Hexagon logo with electric cyan fill and dark centre dot."""
        import math
        pts = []
        for i in range(6):
            a = math.radians(60 * i - 30)
            pts += [cx + r * math.cos(a), cy + r * math.sin(a)]
        canvas.create_polygon(pts, fill=C["accent"], outline="", smooth=False)
        # inner dark hex
        ri = r * 0.55
        pts2 = []
        for i in range(6):
            a = math.radians(60 * i - 30)
            pts2 += [cx + ri * math.cos(a), cy + ri * math.sin(a)]
        canvas.create_polygon(pts2, fill=C["bg_bar"], outline="", smooth=False)
        # centre dot
        rd = r * 0.18
        canvas.create_oval(cx-rd, cy-rd, cx+rd, cy+rd,
                           fill=C["accent"], outline="")


    # ── Pill button helper ─────────────────────────────────────────
    def _btn(self, parent, text, cmd, fg=None, pad=(11, 5), icon=None):
        label = f"{icon}  {text}" if icon else text
        bg_normal = C["bg_bar"]
        fg_normal = fg or C["fg_mid"]
        b = tk.Label(parent, text=label,
            bg=bg_normal, fg=fg_normal,
            font=UIB, padx=pad[0], pady=pad[1],
            cursor="hand2", relief="flat")
        def on_enter(e):
            b.config(bg=C["border"], fg=C["accent"],
                     relief="flat")
        def on_leave(e):
            b.config(bg=bg_normal, fg=fg_normal, relief="flat")
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>", on_enter)
        b.bind("<Leave>", on_leave)
        return b

    def _vsep(self, parent):
        tk.Frame(parent, bg=C["border"], width=1).pack(
            side="left", fill="y", pady=8, padx=4)

    # ── Toolbar ────────────────────────────────────────────────────
    def _build_toolbar(self):
        tb = tk.Frame(self, bg=C["bg_bar"], height=40)
        tb.pack(fill="x", side="top"); tb.pack_propagate(False)
        tk.Frame(self, bg=C["border"], height=1).pack(fill="x", side="top")

        self._btn_run  = self._btn(tb, "Run",       self._run,  fg=C["gold"],  icon="▶")
        self._btn_stop = self._btn(tb, "Stop",       self._stop, fg=C["fg_dim"], icon="■")
        self._btn_run.pack(side="left", padx=(6,1))
        self._btn_stop.pack(side="left", padx=1)
        self._vsep(tb)

        self._btn_over = self._btn(tb, "Over",  self._over, icon="⤵")
        self._btn_into = self._btn(tb, "Into",  self._into, icon="↓")
        self._btn_out  = self._btn(tb, "Out",   self._out,  icon="↑")
        for b in (self._btn_over, self._btn_into, self._btn_out):
            b.pack(side="left", padx=1)
        self._vsep(tb)

        self._btn(tb, "BP",       self._toggle_bp_cursor, fg=C["red"],  icon="⬤").pack(side="left", padx=1)
        self._btn(tb, "Clear BPs", self._clear_bps,        icon="✕").pack(side="left", padx=1)
        self._vsep(tb)
        self._btn(tb, "New",     self._new_file, icon="◻").pack(side="left", padx=1)
        self._btn(tb, "Open",    self._open,     icon="📂").pack(side="left", padx=1)
        self._btn(tb, "Save",    self._save,     icon="💾").pack(side="left", padx=1)
        self._vsep(tb)
        self._btn(tb, "Find",    self._find,         icon="🔍").pack(side="left", padx=1)
        self._btn(tb, "Replace", self._find_replace, icon="⇄").pack(side="left", padx=1)
        self._btn(tb, "→ Line",  self._goto_line,    icon="⌗").pack(side="left", padx=1)

        self._set_debug_btns(False)

    # ── Main layout ────────────────────────────────────────────────
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

    # ── Left panel ─────────────────────────────────────────────────
    def _section_hdr(self, parent, text, icon=""):
        f = tk.Frame(parent, bg=C["bg_bar"], height=28)
        f.pack(fill="x"); f.pack_propagate(False)
        # 3-px cyan accent bar
        tk.Frame(f, bg=C["accent"], width=3).pack(side="left", fill="y")
        # icon + label
        lbl = f"  {icon}  {text.upper()}" if icon else f"  {text.upper()}"
        tk.Label(f, text=lbl, bg=C["bg_bar"],
                 fg=C["fg_mid"], font=UIS).pack(side="left", fill="y")

    def _build_left(self, parent):
        self._section_hdr(parent, "Variables", "◈")
        self._vars = ttk.Treeview(parent,
            columns=("name","val","type"), show="headings",
            style="D.Treeview", height=9)
        for col, w, lbl in [("name",72,"Name"),("val",96,"Value"),("type",56,"Type")]:
            self._vars.heading(col, text=lbl)
            self._vars.column(col, width=w, stretch=True)
        self._vars.pack(fill="both", expand=True)

        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x")

        self._section_hdr(parent, "Call Stack", "⛶")
        self._stack_tv = ttk.Treeview(parent,
            columns=("fn","file","line"), show="headings",
            style="D.Treeview", height=5)
        for col, w, lbl in [("fn",76,"Function"),("file",76,"File"),("line",38,"Ln")]:
            self._stack_tv.heading(col, text=lbl)
            self._stack_tv.column(col, width=w, stretch=True)
        self._stack_tv.pack(fill="both", expand=True)

        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x")

        self._section_hdr(parent, "Watch", "◎")
        wp = tk.Frame(parent, bg=C["bg_panel"]); wp.pack(fill="x", padx=4, pady=3)
        self._watch_entry = tk.Entry(wp, bg=C["bg_editor"], fg=C["fg"],
            insertbackground=C["accent"], relief="flat", font=MONOS,
            highlightthickness=1, highlightcolor=C["accent"],
            highlightbackground=C["border"])
        self._watch_entry.pack(side="left", fill="x", expand=True, ipady=3)
        self._watch_entry.bind("<Return>", lambda e: self._add_watch())
        add_lbl = tk.Label(wp, text=" + ", bg=C["bg_panel"], fg=C["accent"],
            font=UIB, cursor="hand2")
        add_lbl.pack(side="left", padx=(3,0))
        add_lbl.bind("<Button-1>", lambda e: self._add_watch())
        del_lbl = tk.Label(wp, text=" ✕ ", bg=C["bg_panel"], fg=C["rose"],
            font=UIB, cursor="hand2")
        del_lbl.pack(side="left")
        del_lbl.bind("<Button-1>", lambda e: self._del_watch())

        self._watch_tree = ttk.Treeview(parent,
            columns=("expr","value"), show="headings",
            style="D.Treeview", height=5)
        self._watch_tree.heading("expr",  text="Expression")
        self._watch_tree.heading("value", text="Value")
        self._watch_tree.column("expr",  width=90,  stretch=True)
        self._watch_tree.column("value", width=110, stretch=True)
        self._watch_tree.pack(fill="both", expand=True)
        self._watch_tree.bind("<Delete>",    lambda e: self._del_watch())
        self._watch_tree.bind("<BackSpace>", lambda e: self._del_watch())

    # ── Editor ─────────────────────────────────────────────────────
    def _build_editor(self, parent):
        tabbar = tk.Frame(parent, bg=C["bg_bar"], height=30)
        tabbar.pack(fill="x"); tabbar.pack_propagate(False)

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
            insertbackground=C["accent"], insertwidth=2,
            selectbackground=C["bg_sel"], selectforeground=C["fg_white"],
            font=MONO, wrap="none",
            borderwidth=0, relief="flat",
            undo=True, autoseparators=True,
            tabs=("32",), spacing1=2, spacing3=2)
        self._editor.pack(fill="both", expand=True, side="left")

        vsb = tk.Scrollbar(ef, orient="vertical", command=self._editor.yview,
                           bg=C["bg_bar"], troughcolor=C["bg_panel"],
                           width=10, activebackground=C["fg_dim"])
        vsb.pack(side="right", fill="y")
        self._editor.config(
            yscrollcommand=lambda *a: (vsb.set(*a), self._gutter_redraw()))

        hsb = tk.Scrollbar(parent, orient="horizontal",
                           command=self._editor.xview,
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

    # ── Bottom: Output + REPL ──────────────────────────────────────
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
        self._out.tag_config("ok",   foreground=C["green"])

        vsb2 = tk.Scrollbar(out_f, orient="vertical",
            command=self._out.yview,
            bg=C["bg_bar"], troughcolor=C["bg_panel"], width=10)
        vsb2.pack(side="right", fill="y")
        self._out.config(yscrollcommand=vsb2.set)

        repl_f = tk.Frame(nb, bg=C["bg_editor"])
        nb.add(repl_f, text="  REPL  ")
        self._build_repl(repl_f)

    def _build_repl(self, parent):
        self._repl_out = tk.Text(parent, bg=C["bg_editor"], fg=C["fg"],
            font=MONOS, borderwidth=0, relief="flat",
            state="disabled", wrap="word")
        self._repl_out.pack(fill="both", expand=True)
        self._repl_out.tag_config("err",    foreground=C["rose"])
        self._repl_out.tag_config("info",   foreground=C["cyan"])
        self._repl_out.tag_config("prompt", foreground=C["accent"])

        row = tk.Frame(parent, bg=C["bg_input"])
        row.pack(fill="x")
        tk.Frame(row, bg=C["accent"], width=2).pack(side="left", fill="y")
        tk.Label(row, text="  >>>", bg=C["bg_input"],
                 fg=C["accent"], font=MONO).pack(side="left", padx=(6,0))
        self._repl_in = tk.Entry(row, bg=C["bg_input"], fg=C["fg"],
            insertbackground=C["accent"], font=MONO,
            relief="flat", borderwidth=0)
        self._repl_in.pack(fill="x", expand=True, side="left",
                           ipady=5, padx=(8,6), pady=3)
        self._repl_in.bind("<Return>", self._repl_exec)
        self._repl_in.bind("<Up>",     self._repl_hist_up)
        self._repl_in.bind("<Down>",   self._repl_hist_down)
        self._repl_interp = code.InteractiveInterpreter()
        self._repl_write("Python REPL  \u25c6  type any expression\n", "info")

    # ── Status bar ─────────────────────────────────────────────────
    def _build_statusbar(self):
        sb = tk.Frame(self, bg=C["bg_bar"], height=24)
        sb.pack(side="bottom", fill="x"); sb.pack_propagate(False)
        tk.Frame(self, bg=C["accent"], height=1).pack(side="bottom", fill="x")

        # left accent stripe
        tk.Frame(sb, bg=C["accent"], width=3).pack(side="left", fill="y")
        self._st_lbl = tk.Label(sb, text="  Ready",
            bg=C["bg_bar"], fg=C["fg_mid"], font=UIS, anchor="w")
        self._st_lbl.pack(side="left", fill="y", padx=4)

        # right: pos + shortcuts
        self._pos_lbl = tk.Label(sb, text="Ln 1, Col 1",
            bg=C["bg_bar"], fg=C["fg_dim"], font=UIS, padx=10)
        self._pos_lbl.pack(side="right")
        tk.Frame(sb, bg=C["border"], width=1).pack(
            side="right", fill="y", pady=4)

        for key, hint in [("F5","Run"), ("F9","BP"), ("F10","Over"),
                          ("F11","Into"), ("Ctrl+/","Comment"), ("Ctrl+D","Dup")]:
            tk.Label(sb, text=f" {hint} ", bg=C["bg_bar"],
                fg=C["fg_dim"], font=UIS).pack(side="right")
            tk.Label(sb, text=f" {key}", bg=C["bg_bar"],
                fg=C["accent"], font=UIS).pack(side="right")

    def _status(self, msg, bg=None):
        self._st_lbl.config(text=f"  {msg}", bg=bg or C["bg_bar"])

    # ── Keybindings + menu ─────────────────────────────────────────
    def _bind_keys(self):
        self.bind_all("<F5>",        lambda e: self._run())
        self.bind_all("<F9>",        lambda e: self._toggle_bp_cursor())
        self.bind_all("<F10>",       lambda e: self._over())
        self.bind_all("<F11>",       lambda e: self._into())
        self.bind_all("<Shift-F5>",  lambda e: self._stop())
        self.bind_all("<Shift-F11>", lambda e: self._out())
        self.bind_all("<Control-n>", lambda e: self._new_file())
        self.bind_all("<Control-o>", lambda e: self._open())
        self.bind_all("<Control-s>", lambda e: self._save())
        self.bind_all("<Control-f>", lambda e: self._find())
        self.bind_all("<Control-h>", lambda e: self._find_replace())
        self.bind_all("<Control-g>", lambda e: self._goto_line())
        self.bind_all("<Control-slash>", lambda e: self._toggle_comment())
        self.bind_all("<Control-d>", lambda e: self._duplicate_line())

        mc = dict(bg=C["bg_panel"], fg=C["fg"],
                  activebackground=C["accent_dim"],
                  activeforeground=C["accent_hi"],
                  borderwidth=0, relief="flat", font=UI, tearoff=0)
        mb = tk.Menu(self, bg=C["bg_bar"], fg=C["fg_mid"],
                     activebackground=C["border"],
                     activeforeground=C["accent"],
                     borderwidth=0, relief="flat", font=UI)
        self.config(menu=mb)

        fm = tk.Menu(mb, **mc)
        mb.add_cascade(label="  File  ", menu=fm)
        fm.add_command(label="New Python File   Ctrl+N", command=self._new_file)
        fm.add_command(label="New C++ File",             command=self._new_cpp)
        fm.add_command(label="New GLSL File",            command=self._new_glsl)
        fm.add_separator()
        fm.add_command(label="Open…   Ctrl+O", command=self._open)
        fm.add_command(label="Save    Ctrl+S", command=self._save)
        fm.add_command(label="Save As…",       command=self._save_as)
        fm.add_separator()
        fm.add_command(label="Exit",           command=self._on_close)

        em = tk.Menu(mb, **mc)
        mb.add_cascade(label="  Edit  ", menu=em)
        em.add_command(label="Undo          Ctrl+Z", command=lambda: self._editor.edit_undo())
        em.add_command(label="Redo          Ctrl+Y", command=lambda: self._editor.edit_redo())
        em.add_separator()
        em.add_command(label="Find          Ctrl+F", command=self._find)
        em.add_command(label="Find & Replace Ctrl+H", command=self._find_replace)
        em.add_command(label="Go to Line    Ctrl+G", command=self._goto_line)
        em.add_separator()
        em.add_command(label="Toggle Comment  Ctrl+/", command=self._toggle_comment)
        em.add_command(label="Duplicate Line  Ctrl+D", command=self._duplicate_line)

        dm = tk.Menu(mb, **mc)
        mb.add_cascade(label="  Debug  ", menu=dm)
        dm.add_command(label="Run / Continue   F5",        command=self._run)
        dm.add_command(label="Stop             Shift+F5",  command=self._stop)
        dm.add_separator()
        dm.add_command(label="Step Over        F10",       command=self._over)
        dm.add_command(label="Step Into        F11",       command=self._into)
        dm.add_command(label="Step Out         Shift+F11", command=self._out)
        dm.add_separator()
        dm.add_command(label="Toggle Breakpoint  F9",      command=self._toggle_bp_cursor)
        dm.add_command(label="Clear All Breakpoints",      command=self._clear_bps)

    # ── Gutter ─────────────────────────────────────────────────────
    def _gutter_redraw(self, e=None):
        g = self._gutter; g.delete("all")
        i = self._editor.index("@0,0")
        while True:
            dl = self._editor.dlineinfo(i)
            if dl is None: break
            y, h = dl[1], dl[3]; cy = y + h // 2
            ln = int(i.split(".")[0])

            if ln == self._dbg_line:
                g.create_rectangle(0, y, 48, y+h, fill=C["bg_dbg"], outline="")
            if ln in self._bps:
                g.create_oval(5, cy-5, 16, cy+5,
                    fill=C["bp_red"], outline="#FF8888", width=1)
            if ln == self._dbg_line:
                g.create_polygon([18, cy-5, 30, cy, 18, cy+5],
                    fill=C["arrow"], outline="", smooth=False)

            num_c = (C["accent"] if ln == self._dbg_line else
                     C["fg_mid"] if ln in self._bps      else C["gutter_fg"])
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

    # ── Editor helpers ─────────────────────────────────────────────
    def _on_key(self, e=None):
        # Debounce highlight: cancel previous, schedule new in 150 ms
        if self._hl_job: self.after_cancel(self._hl_job)
        self._hl_job = self.after(150, self._do_highlight)
        self._gutter_redraw()
        self._update_pos()

    def _do_highlight(self):
        self._hl_job = None
        highlight(self._editor, self._lang)

    def _auto_indent(self, e=None):
        idx     = self._editor.index("insert")
        line    = self._editor.get(f"{idx} linestart", idx)
        indent  = len(line) - len(line.lstrip())
        stripped = line.rstrip()
        if stripped.endswith(":") or stripped.endswith("{"):
            indent += 4
        elif self._lang == "python" and \
             re.match(r'^\s*(return|pass|raise|break|continue)\b', line):
            indent = max(0, indent - 4)
        self._editor.insert("insert", "\n" + " " * indent)
        return "break"

    def _tab_key(self, e=None):
        self._editor.insert("insert", "    ")
        return "break"

    def _update_pos(self, e=None):
        idx = self._editor.index("insert"); ln, col = idx.split(".")
        try: self._pos_lbl.config(text=f"Ln {ln}, Col {int(col)+1}")
        except: pass

    # FIX 6 — lock editor while Python debugger is running
    def _lock_editor(self):   self._editor.config(state="disabled")
    def _unlock_editor(self): self._editor.config(state="normal")

    # ── Language switch ────────────────────────────────────────────
    def _set_lang(self, lang, name):
        self._lang = lang
        if lang == "python":
            _setup_py_tags(self._editor)
            badge = "🐍 Python"
        elif lang == "cpp":
            _setup_cpp_tags(self._editor)
            badge = "⚙ C / C++"
        else:  # glsl
            _setup_cpp_tags(self._editor)
            badge = "🎨 GLSL"
        self._lang_badge.config(text=f"  {badge}  ")
        highlight(self._editor, lang)
        self._update_labels(name)

    def _update_labels(self, name):
        self._file_lbl.config(text=name)
        self._tab_lbl.config(text=f"  {name}  ")

    # ── Run / Debug ────────────────────────────────────────────────
    def _run(self):
        # C++ / GLSL: syntax-highlight only, no execution in pure Python
        if self._lang in ("cpp", "glsl"):
            lang = self._lang.upper()
            self.log(
                f"[{lang}] Syntax highlighting active.\n"
                f"  To compile C++: use  g++ -std=c++17 file.cpp -lGL -lGLEW -lglfw\n"
                f"  GLSL shaders run on the GPU via an OpenGL host program.\n",
                "info")
            return

        if self._running:
            if self._dbg: self._dbg.cmd_continue()
            return

        src = self._editor.get("1.0", "end-1c").strip()
        if not src: return

        self._out.config(state="normal")
        self._out.delete("1.0", "end")
        self._out.config(state="disabled")

        # FIX 1+2 — stable debug filename
        debug_fname = (os.path.abspath(self._file)
                       if self._file else self._debug_fname)

        self._dbg = Debugger(self)

        # FIX 3 (core) — populate linecache so set_break() validates lines
        src_lines = src.splitlines(True)
        if src_lines and not src_lines[-1].endswith('\n'):
            src_lines[-1] += '\n'
        linecache.cache[debug_fname] = (len(src), None, src_lines, debug_fname)

        if self._bps:
            for ln in sorted(self._bps):
                err = self._dbg.set_break(debug_fname, ln)
                if err: self.log(f"[BP warning line {ln}]: {err}\n", "err")
                else:   self.log(f"[Breakpoint set at line {ln}]\n", "info")
            # FIX — do NOT call set_step() when BPs exist (overrides them)
        else:
            self._dbg.set_step()

        self._running = True
        self._set_debug_btns(True)
        self._btn_run.config(text="▶  Continue")
        self._status(f"Debugging  ◆  {os.path.basename(debug_fname)}",
                     bg=C["gold_dim"])
        self._lock_editor()   # FIX 6

        def runner():
            old_o, old_e = sys.stdout, sys.stderr
            sys.stdout = Redirect(lambda t, tg=None: self.after(0, self.log, t, tg))
            sys.stderr = Redirect(lambda t, tg=None: self.after(0, self.log, t, "err"))
            try:    self._dbg.execute(src, debug_fname)
            finally: sys.stdout, sys.stderr = old_o, old_e

        threading.Thread(target=runner, daemon=True).start()

    def _stop(self):
        if self._dbg: self._dbg.cmd_stop()
        self._running = False; self._dbg_line = None
        self._set_debug_btns(False)
        self._btn_run.config(text="\u25b6  Run")
        self._editor.tag_remove("curdbg", "1.0", "end")
        self._unlock_editor()   # FIX 6
        self._gutter_redraw()
        self._status("Stopped")

    def _over(self):
        if self._running and self._dbg: self._dbg.cmd_next()
    def _into(self):
        if self._running and self._dbg: self._dbg.cmd_step()
    def _out(self):
        if self._running and self._dbg: self._dbg.cmd_return()

    def _set_debug_btns(self, active):
        col = C["fg"] if active else C["fg_dim"]
        for b in (self._btn_stop, self._btn_over, self._btn_into, self._btn_out):
            b.config(fg=col)

    # ── Debugger UI callbacks ──────────────────────────────────────
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
                t  = type(v).__name__
                rv = repr(v)
                if len(rv) > 80: rv = rv[:77] + "\u2026"
            except: t = "?"; rv = "?"
            self._vars.insert("", "end", values=(k, rv, t))

        for r in self._stack_tv.get_children(): self._stack_tv.delete(r)
        for fn, ln, name in stack:
            self._stack_tv.insert("", "end",
                values=(name, os.path.basename(fn), ln))

        self._status(f"⏸  Paused  ◆  Line {lineno}", bg=C["accent_dim"])
        if self._dbg and self._dbg.frame:
            self._eval_watches(self._dbg.frame)

    def on_done(self):
        self._running = False; self._dbg_line = None
        self._set_debug_btns(False)
        self._btn_run.config(text="\u25b6  Run")
        self._editor.tag_remove("curdbg", "1.0", "end")
        self._unlock_editor()   # FIX 6
        self._gutter_redraw()
        for r in self._vars.get_children():    self._vars.delete(r)
        for r in self._stack_tv.get_children(): self._stack_tv.delete(r)
        self._clear_watch_values()
        self._status("Finished  \u2714")
        self.log("\n\u2500\u2500 Finished \u2714 \u2500\u2500\n", "ok")

    def log(self, text, tag=None):
        self._out.config(state="normal")
        if tag: self._out.insert("end", text, tag)
        else:   self._out.insert("end", text)
        self._out.see("end")
        self._out.config(state="disabled")

    # ── REPL  (FIX 3 — use Redirect for InteractiveInterpreter) ───
    def _repl_exec(self, e=None):
        cmd = self._repl_in.get().strip()
        if not cmd: return
        self._repl_hist.append(cmd); self._repl_hidx = -1
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
            self._repl_hidx = max(0,
                len(self._repl_hist)-1 if self._repl_hidx == -1
                else self._repl_hidx - 1)
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

    # ── File operations ────────────────────────────────────────────
    def _load_content(self, content, lang, name, filepath=None):
        """Central loader used by _new_*, _open."""
        self._file        = filepath
        self._debug_fname = (os.path.abspath(filepath)
                             if filepath else _next_untitled())   # FIX 2
        self._clear_bps()
        self._editor.delete("1.0", "end")
        self._editor.insert("1.0", content)
        self._set_lang(lang, name)
        self._gutter_redraw()

    def _new_file(self):
        self._load_content(DEFAULT_PY,   "python", "untitled.py")
        self._status("New Python file")

    def _new_cpp(self):
        self._load_content(DEFAULT_CPP,  "cpp",    "untitled.cpp")
        self._status("New C++ file")

    def _new_glsl(self):
        self._load_content(DEFAULT_GLSL, "glsl",   "untitled.frag")
        self._status("New GLSL file")

    def _open(self, path=None):
        if path is None:
            path = filedialog.askopenfilename(filetypes=[
                ("All supported",
                 "*.py *.cpp *.cxx *.cc *.c *.h *.hpp "
                 "*.glsl *.vert *.frag *.geom *.comp"),
                ("Python files",  "*.py"),
                ("C / C++ files", "*.cpp *.cxx *.cc *.c *.h *.hpp"),
                ("GLSL shaders",  "*.glsl *.vert *.frag *.geom *.comp"),
                ("All files",     "*.*"),
            ])
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as f: src = f.read()
        except Exception as ex:
            self.log(f"[Open error] {ex}\n", "err"); return
        lang = detect_lang(path)
        self._load_content(src, lang, os.path.basename(path), filepath=path)
        self._status(f"Opened  \u25c6  {os.path.basename(path)}")

    def _save(self):
        if self._file:
            try:
                src = self._editor.get("1.0", "end-1c")
                with open(self._file, "w", encoding="utf-8") as f:
                    f.write(src)
                self._debug_fname = os.path.abspath(self._file)   # FIX 2
                new_lang = detect_lang(self._file)
                if new_lang != self._lang:
                    self._set_lang(new_lang, os.path.basename(self._file))
                self.log(f"Saved \u2192 {self._file}\n", "info")
                self._status(f"Saved  \u25c6  {os.path.basename(self._file)}")
            except Exception as ex:
                self.log(f"[Save error] {ex}\n", "err")
        else:
            self._save_as()

    def _save_as(self):
        ext_map = {"python": ".py", "cpp": ".cpp", "glsl": ".frag"}
        p = filedialog.asksaveasfilename(
            defaultextension=ext_map.get(self._lang, ".py"),
            filetypes=[
                ("Python",      "*.py"),
                ("C / C++",     "*.cpp *.c *.h *.hpp"),
                ("GLSL shader", "*.glsl *.vert *.frag *.geom *.comp"),
                ("All",         "*.*"),
            ])
        if not p: return
        self._file = p; self._save()

    # ── Find ───────────────────────────────────────────────────────
    def _find(self):
        if self._find_win and self._find_win.winfo_exists():
            self._find_win.lift(); return
        win = tk.Toplevel(self)
        win.title("Find"); win.geometry("360x68")
        win.configure(bg=C["bg_input"]); win.resizable(False, False)
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
                self._editor.tag_add("found", pos, end); start = end
            first = self._editor.tag_ranges("found")
            if first: self._editor.see(first[0])

        fe.bind("<Return>", do_find)
        tk.Button(row, text="Find", command=do_find,
            bg=C["accent"], fg="white",
            activebackground=C["accent_hi"], activeforeground="white",
            font=UIB, relief="flat", borderwidth=0,
            padx=14, pady=3, cursor="hand2").pack(side="left")

    # ══ 1. WATCH PANEL ════════════════════════════════════════════════
    def _add_watch(self):
        expr = self._watch_entry.get().strip()
        if not expr or expr in self._watches: return
        self._watches.append(expr)
        self._watch_tree.insert("", "end", iid=expr, values=(expr, "—"))
        self._watch_entry.delete(0, "end")
        if self._dbg and self._dbg.frame:
            self._eval_watches(self._dbg.frame)

    def _del_watch(self):
        for iid in self._watch_tree.selection():
            expr = self._watch_tree.item(iid, "values")[0]
            self._watches = [w for w in self._watches if w != expr]
            self._watch_tree.delete(iid)

    def _eval_watches(self, frame):
        g, l = frame.f_globals, frame.f_locals
        for expr in self._watches:
            try:    val = repr(eval(expr, g, l))[:80]
            except Exception as ex: val = f"<{ex}>"
            self._watch_tree.item(expr, values=(expr, val))

    def _clear_watch_values(self):
        for expr in self._watches:
            self._watch_tree.item(expr, values=(expr, "—"))

    # ══ 2. FIND & REPLACE ════════════════════════════════════════════
    def _find_replace(self):
        if self._find_replace_win and self._find_replace_win.winfo_exists():
            self._find_replace_win.lift(); return
        win = tk.Toplevel(self)
        win.title("Find & Replace"); win.geometry("420x130")
        win.configure(bg=C["bg_input"]); win.resizable(False, False)
        self._find_replace_win = win
        tk.Frame(win, bg=C["accent"], height=2).pack(fill="x")

        grid = tk.Frame(win, bg=C["bg_input"]); grid.pack(fill="x", padx=12, pady=8)
        for row_i, label in enumerate(("Find:", "Replace:")):
            tk.Label(grid, text=label, bg=C["bg_input"], fg=C["fg_dim"],
                font=UIB, width=8, anchor="w").grid(row=row_i, column=0, pady=3)
        fe = tk.Entry(grid, bg=C["bg_editor"], fg=C["fg"],
            insertbackground=C["accent"], font=MONOS, relief="flat",
            highlightthickness=1, highlightbackground=C["border"],
            highlightcolor=C["accent"])
        fe.grid(row=0, column=1, sticky="ew", padx=(6,0), ipady=3)
        re_e = tk.Entry(grid, bg=C["bg_editor"], fg=C["fg"],
            insertbackground=C["accent"], font=MONOS, relief="flat",
            highlightthickness=1, highlightbackground=C["border"],
            highlightcolor=C["accent"])
        re_e.grid(row=1, column=1, sticky="ew", padx=(6,0), ipady=3)
        grid.columnconfigure(1, weight=1)
        fe.focus_set()

        btnrow = tk.Frame(win, bg=C["bg_input"]); btnrow.pack(fill="x", padx=12, pady=(0,8))
        def _mk(text, cmd):
            b = tk.Button(btnrow, text=text, command=cmd,
                bg=C["bg_bar"], fg=C["accent"], activebackground=C["accent_dim"],
                activeforeground=C["accent_hi"], relief="flat", font=UIB,
                padx=10, pady=3, cursor="hand2")
            b.pack(side="left", padx=3); return b

        def do_find(ev=None):
            self._editor.tag_remove("found", "1.0", "end")
            q = fe.get()
            if not q: return
            start = "1.0"
            while True:
                pos = self._editor.search(q, start, stopindex="end")
                if not pos: break
                self._editor.tag_add("found", pos, f"{pos}+{len(q)}c")
                start = f"{pos}+{len(q)}c"
            first = self._editor.tag_ranges("found")
            if first: self._editor.see(first[0])

        def do_replace_all():
            q, r = fe.get(), re_e.get()
            if not q: return
            src = self._editor.get("1.0", "end-1c")
            count = src.count(q)
            if count == 0: return
            new_src = src.replace(q, r)
            self._editor.delete("1.0", "end")
            self._editor.insert("1.0", new_src)
            self._do_highlight()
            self.log(f"[Replace] {count} occurrence(s) replaced.\n", "info")

        fe.bind("<Return>", do_find)
        _mk("Find All", do_find)
        _mk("Replace All", do_replace_all)

    # ══ 3. GOTO LINE ═════════════════════════════════════════════════
    def _goto_line(self):
        win = tk.Toplevel(self)
        win.title("Go to Line"); win.geometry("280x68")
        win.configure(bg=C["bg_input"]); win.resizable(False, False)
        win.transient(self); win.grab_set()
        tk.Frame(win, bg=C["accent"], height=2).pack(fill="x")

        row = tk.Frame(win, bg=C["bg_input"]); row.pack(fill="x", padx=12, pady=12)
        tk.Label(row, text="Line:", bg=C["bg_input"], fg=C["fg_dim"],
            font=UIB).pack(side="left")
        entry = tk.Entry(row, bg=C["bg_editor"], fg=C["fg"],
            insertbackground=C["accent"], font=MONOS, relief="flat",
            highlightthickness=1, highlightbackground=C["border"],
            highlightcolor=C["accent"], width=8)
        entry.pack(side="left", padx=8, ipady=3)
        entry.focus_set()

        def go(ev=None):
            try:
                ln = int(entry.get())
                total = int(self._editor.index("end-1c").split(".")[0])
                ln = max(1, min(ln, total))
                self._editor.mark_set("insert", f"{ln}.0")
                self._editor.see(f"{ln}.0")
                self._update_pos()
            except ValueError: pass
            win.destroy()

        entry.bind("<Return>", go)
        tk.Button(row, text="Go", command=go,
            bg=C["accent"], fg=C["bg_editor"],
            activebackground=C["accent_hi"], relief="flat",
            font=UIB, padx=12, pady=2, cursor="hand2").pack(side="left")

    # ══ 4. TOGGLE COMMENT ════════════════════════════════════════════
    def _toggle_comment(self):
        prefix = {"python": "# ", "cpp": "// ", "glsl": "// "}.get(self._lang, "# ")
        try:
            sel_start = self._editor.index("sel.first linestart")
            sel_end   = self._editor.index("sel.last lineend")
        except tk.TclError:
            sel_start = self._editor.index("insert linestart")
            sel_end   = self._editor.index("insert lineend")

        lines = self._editor.get(sel_start, sel_end).split("\n")
        # if ALL non-empty lines start with prefix → uncomment, else comment
        non_empty = [l for l in lines if l.strip()]
        all_commented = non_empty and all(l.lstrip().startswith(prefix.rstrip()) for l in non_empty)

        new_lines = []
        for line in lines:
            if all_commented:
                idx = line.find(prefix.rstrip())
                if idx != -1:
                    new_lines.append(line[:idx] + line[idx+len(prefix):])
                else:
                    new_lines.append(line)
            else:
                new_lines.append(prefix + line)

        self._editor.delete(sel_start, sel_end)
        self._editor.insert(sel_start, "\n".join(new_lines))
        self._do_highlight()
        return "break"

    # ══ 5. DUPLICATE LINE ════════════════════════════════════════════
    def _duplicate_line(self):
        idx  = self._editor.index("insert")
        line = self._editor.get(f"{idx} linestart", f"{idx} lineend")
        ln   = int(idx.split(".")[0])
        self._editor.insert(f"{ln}.end", "\n" + line)
        self._gutter_redraw()
        return "break"

    # FIX 5 — clean shutdown stops debug thread before destroy
    def _on_close(self):
        if self._running and self._dbg: self._dbg.cmd_stop()
        self.destroy()


# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    fp = sys.argv[1] if len(sys.argv) > 1 else None
    NanoPyDebug(filepath=fp).mainloop()