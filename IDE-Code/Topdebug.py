"""
╔══════════════════════════════════════════════════════════════════════╗
║   T O P D E B U G   v2.0  —  Advanced IDE                           ║
║   Pure Python · stdlib only · tkinter UI                             ║
║                                                                      ║
║   NEW FEATURES vs v1.0:                                              ║
║   • Multi-tab editor (open & manage many files at once)              ║
║   • Code minimap (right-side overview of entire file)                ║
║   • Breadcrumb navigation bar (file › class › function)              ║
║   • IntelliSense autocomplete popup (Ctrl+Space / auto-trigger)      ║
║   • Bracket / quote pair matching & auto-close                       ║
║   • Find & Replace dialog with regex + case options                  ║
║   • Symbol Outline panel (functions, classes, variables)             ║
║   • Code folding (collapse/expand blocks via gutter)                 ║
║   • Light / Dark / High-Contrast themes with live switch             ║
║   • Command Palette (Ctrl+Shift+P) — fuzzy search all commands       ║
║   • Git-style change gutter (modified / added / deleted lines)       ║
║   • Persistent settings (window size, recent files, theme)           ║
║   • Improved status bar: encoding, eol, git branch, clock            ║
║   • REPL history up/down, REPL clear button                          ║
║   • Line/column jump dialog (Ctrl+G)                                 ║
║   • Duplicate-line (Ctrl+D), move-line up/down (Alt+Up/Down)         ║
║   • Toggle comment (Ctrl+/)                                          ║
║   • Indent / un-indent selection (Tab / Shift+Tab)                   ║
║   • All original debug features preserved & enhanced                  ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys, os, bdb, threading, traceback, io, tokenize, token
import code as _code_mod, re, subprocess, tempfile, json, time, ast
from collections import deque
from datetime import datetime

# ═══════════════════════════════════════════════════════════════
#  THEME DEFINITIONS
# ═══════════════════════════════════════════════════════════════
THEMES = {}

THEMES["Dark (VS2026)"] = dict(
    bg          = "#0d1117",
    bg_panel    = "#161b22",
    bg_sidebar  = "#1c2128",
    bg_toolbar  = "#21262d",
    bg_menubar  = "#161b22",
    bg_tab      = "#1c2128",
    bg_tab_act  = "#0d1117",
    bg_tab_bar  = "#161b22",
    bg_select   = "#1f3a5f",
    bg_curline  = "#161b22",
    bg_bp       = "#2d1515",
    bg_debug    = "#0e2318",
    bg_bottom   = "#161b22",
    bg_hover    = "#2a3140",
    bg_statusbar     = "#1158a8",
    bg_statusbar_dbg = "#b5440a",
    bg_grip     = "#30363d",
    fg          = "#e6edf3",
    fg_dim      = "#7d8590",
    fg_muted    = "#484f58",
    fg_white    = "#ffffff",
    fg_tab      = "#7d8590",
    fg_tab_act  = "#e6edf3",
    fg_panel_hdr= "#e6edf3",
    accent      = "#1f6feb",
    accent2     = "#388bfd",
    accent_glow = "#1158a8",
    border      = "#30363d",
    border_act  = "#1f6feb",
    border_dark = "#21262d",
    bp_red      = "#ff4444",
    bp_glow     = "#7a1515",
    arrow       = "#ffd700",
    arrow_glow  = "#5a4800",
    gutter_bg   = "#161b22",
    gutter_fg   = "#484f58",
    gutter_ln   = "#6e7681",
    mod_line    = "#1b4620",
    add_line    = "#1b4620",
    del_line    = "#6e1111",
    s_kw   = "#ff7b72",
    s_bi   = "#79c0ff",
    s_fn   = "#d2a8ff",
    s_var  = "#e6edf3",
    s_str  = "#a5d6ff",
    s_num  = "#79c0ff",
    s_cmt  = "#8b949e",
    s_op   = "#ff7b72",
    s_self = "#79c0ff",
    s_pp   = "#f0883e",
    s_type = "#ffa657",
    s_dec  = "#ffa657",
    red    = "#ff7b72",
    green  = "#56d364",
    cyan   = "#39d5ff",
    orange = "#ffa657",
    yellow = "#e3b341",
    purple = "#d2a8ff",
    pink   = "#f778ba",
    ac_popup_bg  = "#1c2128",
    ac_popup_sel = "#1f6feb",
    ac_popup_fg  = "#e6edf3",
    minimap_bg   = "#0d1117",
    minimap_fg   = "#30363d",
    fold_fg      = "#484f58",
    fold_bg      = "#21262d",
)

THEMES["Light (Classic)"] = dict(
    bg          = "#ffffff",
    bg_panel    = "#f3f3f3",
    bg_sidebar  = "#e8e8e8",
    bg_toolbar  = "#f0f0f0",
    bg_menubar  = "#f0f0f0",
    bg_tab      = "#ececec",
    bg_tab_act  = "#ffffff",
    bg_tab_bar  = "#e8e8e8",
    bg_select   = "#add6ff",
    bg_curline  = "#f5f5f5",
    bg_bp       = "#ffe8e8",
    bg_debug    = "#dff0d8",
    bg_bottom   = "#f3f3f3",
    bg_hover    = "#e0e0e0",
    bg_statusbar     = "#007acc",
    bg_statusbar_dbg = "#ca5100",
    bg_grip     = "#d0d0d0",
    fg          = "#1e1e1e",
    fg_dim      = "#717171",
    fg_muted    = "#aaaaaa",
    fg_white    = "#ffffff",
    fg_tab      = "#717171",
    fg_tab_act  = "#1e1e1e",
    fg_panel_hdr= "#1e1e1e",
    accent      = "#007acc",
    accent2     = "#0098ff",
    accent_glow = "#005a9e",
    border      = "#d0d0d0",
    border_act  = "#007acc",
    border_dark = "#e0e0e0",
    bp_red      = "#e51400",
    bp_glow     = "#ffcccc",
    arrow       = "#c8a000",
    arrow_glow  = "#fff3aa",
    gutter_bg   = "#f3f3f3",
    gutter_fg   = "#aaaaaa",
    gutter_ln   = "#999999",
    mod_line    = "#fcefa1",
    add_line    = "#d4edda",
    del_line    = "#f8d7da",
    s_kw   = "#0000ff",
    s_bi   = "#267f99",
    s_fn   = "#795e26",
    s_var  = "#001080",
    s_str  = "#a31515",
    s_num  = "#098658",
    s_cmt  = "#008000",
    s_op   = "#000000",
    s_self = "#267f99",
    s_pp   = "#af00db",
    s_type = "#267f99",
    s_dec  = "#795e26",
    red    = "#e51400",
    green  = "#008000",
    cyan   = "#007acc",
    orange = "#ff8c00",
    yellow = "#e6a817",
    purple = "#6f42c1",
    pink   = "#d63384",
    ac_popup_bg  = "#ffffff",
    ac_popup_sel = "#007acc",
    ac_popup_fg  = "#1e1e1e",
    minimap_bg   = "#f3f3f3",
    minimap_fg   = "#d0d0d0",
    fold_fg      = "#aaaaaa",
    fold_bg      = "#e8e8e8",
)

THEMES["High Contrast"] = dict(
    bg          = "#000000",
    bg_panel    = "#0a0a0a",
    bg_sidebar  = "#111111",
    bg_toolbar  = "#0a0a0a",
    bg_menubar  = "#000000",
    bg_tab      = "#111111",
    bg_tab_act  = "#000000",
    bg_tab_bar  = "#0a0a0a",
    bg_select   = "#1166cc",
    bg_curline  = "#0a0a0a",
    bg_bp       = "#3b0000",
    bg_debug    = "#003300",
    bg_bottom   = "#0a0a0a",
    bg_hover    = "#1a1a1a",
    bg_statusbar     = "#0066cc",
    bg_statusbar_dbg = "#cc4400",
    bg_grip     = "#333333",
    fg          = "#ffffff",
    fg_dim      = "#aaaaaa",
    fg_muted    = "#555555",
    fg_white    = "#ffffff",
    fg_tab      = "#aaaaaa",
    fg_tab_act  = "#ffffff",
    fg_panel_hdr= "#ffffff",
    accent      = "#3399ff",
    accent2     = "#55aaff",
    accent_glow = "#0055aa",
    border      = "#444444",
    border_act  = "#3399ff",
    border_dark = "#222222",
    bp_red      = "#ff0000",
    bp_glow     = "#660000",
    arrow       = "#ffff00",
    arrow_glow  = "#555500",
    gutter_bg   = "#000000",
    gutter_fg   = "#555555",
    gutter_ln   = "#888888",
    mod_line    = "#003300",
    add_line    = "#003300",
    del_line    = "#440000",
    s_kw   = "#ff6699",
    s_bi   = "#66ccff",
    s_fn   = "#cc99ff",
    s_var  = "#ffffff",
    s_str  = "#99ddff",
    s_num  = "#66ff66",
    s_cmt  = "#999999",
    s_op   = "#ffaa44",
    s_self = "#66ccff",
    s_pp   = "#ffaa44",
    s_type = "#ffcc66",
    s_dec  = "#ffcc66",
    red    = "#ff4444",
    green  = "#44ff44",
    cyan   = "#44ffff",
    orange = "#ffaa44",
    yellow = "#ffff44",
    purple = "#cc99ff",
    pink   = "#ff66aa",
    ac_popup_bg  = "#111111",
    ac_popup_sel = "#3399ff",
    ac_popup_fg  = "#ffffff",
    minimap_bg   = "#000000",
    minimap_fg   = "#333333",
    fold_fg      = "#555555",
    fold_bg      = "#111111",
)

C = dict(THEMES["Dark (VS2026)"])  # active theme (mutable reference)

MONO   = ("Consolas", 11)
MONO_S = ("Consolas", 10)
UI     = ("Segoe UI", 9)
UI_B   = ("Segoe UI", 9, "bold")
UI_S   = ("Segoe UI", 8)
UI_T   = ("Segoe UI", 10)

SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".topdebug_settings.json")

def load_settings():
    try:
        with open(SETTINGS_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def save_settings(d):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(d, f, indent=2)
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════
#  PYTHON SYNTAX KEYWORDS / BUILTINS
# ═══════════════════════════════════════════════════════════════
KEYWORDS = {
    'False','None','True','and','as','assert','async','await','break',
    'class','continue','def','del','elif','else','except','finally',
    'for','from','global','if','import','in','is','lambda','nonlocal',
    'not','or','pass','raise','return','try','while','with','yield'
}
BUILTINS = {
    'abs','all','any','bin','bool','bytes','callable','chr','compile',
    'dict','dir','divmod','enumerate','eval','exec','filter','float',
    'format','frozenset','getattr','globals','hasattr','hash','help',
    'hex','id','input','int','isinstance','issubclass','iter','len',
    'list','locals','map','max','min','next','object','oct','open',
    'ord','pow','print','property','range','repr','reversed','round',
    'set','setattr','slice','sorted','staticmethod','str','sum',
    'super','tuple','type','vars','zip','Exception','ValueError',
    'TypeError','KeyError','IndexError','AttributeError',
    'NotImplementedError','RuntimeError','StopIteration','OSError',
    'FileNotFoundError','PermissionError','ImportError','NameError',
}
DECORATORS = {'property', 'staticmethod', 'classmethod', 'abstractmethod',
              'dataclass', 'override', 'cache', 'lru_cache', 'wraps'}

# ═══════════════════════════════════════════════════════════════
#  C++ / GLSL KEYWORDS
# ═══════════════════════════════════════════════════════════════
CPP_KEYWORDS = {
    'alignas','alignof','and','and_eq','asm','auto','bitand','bitor',
    'bool','break','case','catch','char','char8_t','char16_t','char32_t',
    'class','compl','concept','const','consteval','constexpr','constinit',
    'const_cast','continue','co_await','co_return','co_yield','decltype',
    'default','delete','do','double','dynamic_cast','else','enum','explicit',
    'export','extern','false','float','for','friend','goto','if','inline',
    'int','long','mutable','namespace','new','noexcept','not','not_eq',
    'nullptr','operator','or','or_eq','private','protected','public',
    'register','reinterpret_cast','requires','return','short','signed',
    'sizeof','static','static_assert','static_cast','struct','switch',
    'template','this','thread_local','throw','true','try','typedef',
    'typeid','typename','union','unsigned','using','virtual','void',
    'volatile','wchar_t','while','xor','xor_eq','override','final',
    'define','include','ifdef','ifndef','endif','pragma','undef','elif',
}
CPP_BUILTINS = {
    'std','cout','cin','cerr','endl','string','vector','map','set',
    'unordered_map','unordered_set','list','deque','queue','stack',
    'pair','tuple','array','optional','variant','any','function',
    'shared_ptr','unique_ptr','weak_ptr','make_shared','make_unique',
    'printf','scanf','malloc','free','memset','memcpy','strlen',
    'size_t','ptrdiff_t','int8_t','int16_t','int32_t','int64_t',
    'uint8_t','uint16_t','uint32_t','uint64_t',
    'GLuint','GLint','GLfloat','GLdouble','GLenum','GLboolean',
    'GLsizei','GLchar','GLvoid','GLbitfield','GLclampf',
    'glGenVertexArrays','glBindVertexArray','glGenBuffers','glBindBuffer',
    'glBufferData','glVertexAttribPointer','glEnableVertexAttribArray',
    'glCreateShader','glShaderSource','glCompileShader','glCreateProgram',
    'glAttachShader','glLinkProgram','glUseProgram','glDeleteShader',
    'glClear','glClearColor','glEnable','glDisable','glViewport',
    'GL_VERTEX_SHADER','GL_FRAGMENT_SHADER','GL_ARRAY_BUFFER',
    'GL_STATIC_DRAW','GL_TRIANGLES','GL_COLOR_BUFFER_BIT','GL_DEPTH_TEST',
}
GLSL_KEYWORDS = {
    'attribute','const','uniform','varying','break','continue','do',
    'for','while','if','else','in','out','inout','float','int','uint',
    'void','bool','true','false','lowp','mediump','highp','precision',
    'invariant','discard','return','struct','sampler2D','sampler3D',
    'samplerCube','vec2','vec3','vec4','bvec2','bvec3','bvec4',
    'ivec2','ivec3','ivec4','uvec2','uvec3','uvec4',
    'mat2','mat3','mat4','layout','location','binding',
    'version','core','es','extension','require','enable',
}
GLSL_BUILTINS = {
    'gl_Position','gl_FragCoord','gl_FragColor','gl_PointSize',
    'radians','degrees','sin','cos','tan','asin','acos','atan',
    'pow','exp','log','sqrt','abs','sign','floor','ceil','fract',
    'min','max','clamp','mix','step','smoothstep','length','distance',
    'dot','cross','normalize','reflect','refract','texture','texture2D',
}

# ═══════════════════════════════════════════════════════════════
#  PYTHON HIGHLIGHTER
# ═══════════════════════════════════════════════════════════════
def rehighlight(widget):
    src = widget.get("1.0", "end-1c")
    for tag in ("kw","bi","fn","var","str_","num","cmt","op","self_","dec"):
        widget.tag_remove(tag, "1.0", "end")
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except tokenize.TokenError:
        return
    prev = None
    for tok in toks:
        tt, ts, (sr, sc), (er, ec), _ = tok
        s, e = f"{sr}.{sc}", f"{er}.{ec}"
        if tt == token.NAME:
            if ts == "self":
                widget.tag_add("self_", s, e)
            elif ts in KEYWORDS:
                widget.tag_add("kw", s, e)
            elif ts in BUILTINS:
                widget.tag_add("bi", s, e)
            elif prev and prev[1] in ("def", "class"):
                widget.tag_add("fn", s, e)
            elif prev and prev[1] == "@":
                widget.tag_add("dec", s, e)
            else:
                widget.tag_add("var", s, e)
        elif tt == token.STRING:
            widget.tag_add("str_", s, e)
        elif tt == token.NUMBER:
            widget.tag_add("num", s, e)
        elif tt == token.COMMENT:
            widget.tag_add("cmt", s, e)
        elif tt == token.OP:
            widget.tag_add("op", s, e)
        if tt not in (token.NEWLINE, token.NL, token.INDENT,
                      token.DEDENT, token.ENCODING, token.COMMENT,
                      token.ERRORTOKEN):
            prev = tok

def setup_tags(widget):
    widget.tag_config("kw",    foreground=C["s_kw"],  font=(*MONO[:1], MONO[1], "bold"))
    widget.tag_config("bi",    foreground=C["s_bi"])
    widget.tag_config("fn",    foreground=C["s_fn"])
    widget.tag_config("var",   foreground=C["s_var"])
    widget.tag_config("str_",  foreground=C["s_str"])
    widget.tag_config("num",   foreground=C["s_num"])
    widget.tag_config("cmt",   foreground=C["s_cmt"],  font=(*MONO[:1], MONO[1], "italic"))
    widget.tag_config("op",    foreground=C["s_op"])
    widget.tag_config("self_", foreground=C["s_self"])
    widget.tag_config("dec",   foreground=C["s_dec"],  font=(*MONO[:1], MONO[1], "italic"))
    widget.tag_config("curdbg",   background=C["bg_debug"])
    widget.tag_config("bp_ln",    background=C["bg_bp"])
    widget.tag_config("found",    background="#3d2b00", foreground="#ffd700")
    widget.tag_config("curline",  background=C["bg_curline"])
    widget.tag_config("match_br", background=C["bg_select"], foreground=C["fg_white"])
    widget.tag_config("mod_gutter", background=C["mod_line"])

# ═══════════════════════════════════════════════════════════════
#  C++ / GLSL HIGHLIGHTER
# ═══════════════════════════════════════════════════════════════
def _regex_highlight_cpp(widget, src, lang="cpp"):
    kw_set = CPP_KEYWORDS if lang in ("cpp","glsl") else CPP_KEYWORDS
    bi_set = GLSL_BUILTINS if lang == "glsl" else CPP_BUILTINS
    if lang == "glsl":
        kw_set = GLSL_KEYWORDS
    for tag in ("kw","bi","fn","str_","num","cmt","op","pp"):
        widget.tag_remove(tag, "1.0", "end")
    lines = src.split("\n")
    in_block = False
    for lineno, line in enumerate(lines, 1):
        i = 0; n = len(line)
        if in_block:
            end = line.find("*/")
            if end == -1:
                widget.tag_add("cmt", f"{lineno}.0", f"{lineno}.{n}")
                continue
            else:
                widget.tag_add("cmt", f"{lineno}.0", f"{lineno}.{end+2}")
                i = end + 2; in_block = False
        while i < n:
            if line[i:i+2] == "/*":
                end = line.find("*/", i+2)
                if end == -1:
                    widget.tag_add("cmt", f"{lineno}.{i}", f"{lineno}.{n}")
                    in_block = True; i = n; continue
                else:
                    widget.tag_add("cmt", f"{lineno}.{i}", f"{lineno}.{end+2}")
                    i = end + 2; continue
            if line[i:i+2] == "//":
                widget.tag_add("cmt", f"{lineno}.{i}", f"{lineno}.{n}"); break
            if i == 0 and line.lstrip().startswith("#"):
                widget.tag_add("pp", f"{lineno}.0", f"{lineno}.1")
                for m2 in re.finditer(r'\b([a-zA-Z_]\w*)\b', line):
                    word = m2.group(1); cs, ce = m2.start(), m2.end()
                    if word in kw_set:
                        widget.tag_add("kw", f"{lineno}.{cs}", f"{lineno}.{ce}")
                    elif word in bi_set:
                        widget.tag_add("bi", f"{lineno}.{cs}", f"{lineno}.{ce}")
                break
            if line[i] in ('"', "'"):
                q = line[i]; j = i + 1
                while j < n:
                    if line[j] == '\\': j += 2; continue
                    if line[j] == q: j += 1; break
                    j += 1
                widget.tag_add("str_", f"{lineno}.{i}", f"{lineno}.{j}")
                i = j; continue
            m = re.match(r'(0x[0-9a-fA-F]+|0b[01]+|\d+\.?\d*([eE][+-]?\d+)?[fFlLuU]*)', line[i:])
            if m and (i == 0 or (not line[i-1].isalnum() and line[i-1] != '_')):
                j = i + len(m.group(0))
                widget.tag_add("num", f"{lineno}.{i}", f"{lineno}.{j}")
                i = j; continue
            m = re.match(r'[a-zA-Z_]\w*', line[i:])
            if m:
                word = m.group(0); j = i + len(word)
                if word in kw_set:
                    widget.tag_add("kw", f"{lineno}.{i}", f"{lineno}.{j}")
                elif word in bi_set:
                    widget.tag_add("bi", f"{lineno}.{i}", f"{lineno}.{j}")
                elif j < n and line[j] == '(':
                    widget.tag_add("fn", f"{lineno}.{i}", f"{lineno}.{j}")
                i = j; continue
            if line[i] in '+-*/%=<>!&|^~?:;,()[]{}':
                widget.tag_add("op", f"{lineno}.{i}", f"{lineno}.{i+1}")
            i += 1

def setup_tags_cpp(widget):
    widget.tag_config("kw",    foreground=C["s_kw"],  font=(*MONO[:1], MONO[1], "bold"))
    widget.tag_config("bi",    foreground=C["s_bi"])
    widget.tag_config("fn",    foreground=C["s_fn"])
    widget.tag_config("str_",  foreground=C["s_str"])
    widget.tag_config("num",   foreground=C["s_num"])
    widget.tag_config("cmt",   foreground=C["s_cmt"],  font=(*MONO[:1], MONO[1], "italic"))
    widget.tag_config("op",    foreground=C["s_op"])
    widget.tag_config("pp",    foreground=C["s_pp"],   font=(*MONO[:1], MONO[1], "bold"))
    widget.tag_config("curdbg",   background=C["bg_debug"])
    widget.tag_config("bp_ln",    background=C["bg_bp"])
    widget.tag_config("found",    background="#3d2b00", foreground="#ffd700")
    widget.tag_config("curline",  background=C["bg_curline"])
    widget.tag_config("match_br", background=C["bg_select"], foreground=C["fg_white"])

# ═══════════════════════════════════════════════════════════════
#  LANGUAGE DETECTION
# ═══════════════════════════════════════════════════════════════
def detect_language(path):
    if path is None: return "python"
    ext = os.path.splitext(path)[1].lower()
    if ext in ('.cpp','.cxx','.cc','.c','.h','.hpp','.hxx'): return "cpp"
    if ext in ('.glsl','.vert','.frag','.geom','.comp','.tesc','.tese'): return "glsl"
    return "python"

# ═══════════════════════════════════════════════════════════════
#  PYTHON AUTOCOMPLETE ENGINE
# ═══════════════════════════════════════════════════════════════
class Completer:
    SNIPPET_KW = {
        "def":   "def name(args):\n    pass",
        "class": "class Name:\n    def __init__(self):\n        pass",
        "if":    "if condition:\n    pass",
        "for":   "for item in iterable:\n    pass",
        "while": "while condition:\n    pass",
        "try":   "try:\n    pass\nexcept Exception as e:\n    pass",
        "with":  "with expr as var:\n    pass",
        "import":"import module",
        "from":  "from module import name",
        "lambda":"lambda x: x",
    }

    def get_completions(self, src, pos_line, pos_col):
        lines = src.split("\n")
        if pos_line < 1 or pos_line > len(lines): return []
        line = lines[pos_line - 1][:pos_col]
        m = re.search(r'[\w\.]+$', line)
        if not m: return []
        prefix = m.group(0)
        results = []
        if '.' in prefix:
            parts = prefix.rsplit('.', 1)
            obj_name, attr_prefix = parts[0], parts[1]
            try:
                globs = {}
                exec(src, globs)
                obj = eval(obj_name, globs)
                for attr in dir(obj):
                    if attr.startswith(attr_prefix):
                        kind = "method" if callable(getattr(obj, attr, None)) else "attr"
                        results.append((attr, kind, obj_name))
            except Exception:
                pass
        else:
            for kw in sorted(KEYWORDS):
                if kw.startswith(prefix): results.append((kw, "keyword", ""))
            for bi in sorted(BUILTINS):
                if bi.startswith(prefix): results.append((bi, "builtin", ""))
            for ln in src.split("\n"):
                m2 = re.match(r'\s*(def|class)\s+(\w+)', ln)
                if m2:
                    name = m2.group(2)
                    kind = m2.group(1)
                    if name.startswith(prefix):
                        results.append((name, kind, ""))
            for ln in src.split("\n"):
                m3 = re.match(r'\s*(\w+)\s*=', ln)
                if m3:
                    name = m3.group(1)
                    if name.startswith(prefix) and name not in KEYWORDS:
                        if not any(r[0] == name for r in results):
                            results.append((name, "var", ""))
        return results[:40]

# ═══════════════════════════════════════════════════════════════
#  SYMBOL OUTLINE BUILDER
# ═══════════════════════════════════════════════════════════════
def build_outline(src):
    outline = []
    for i, line in enumerate(src.split("\n"), 1):
        m = re.match(r'^(\s*)(def|class)\s+(\w+)', line)
        if m:
            indent = len(m.group(1))
            kind   = m.group(2)
            name   = m.group(3)
            outline.append((i, indent, kind, name))
    return outline

# ═══════════════════════════════════════════════════════════════
#  DEBUGGER BACKEND
#  FIX: Override canonic() so that the in-memory filename used in
#       compile() exactly matches what bdb stores for breakpoints.
#       Also fixed execute() to use the same canonical filename.
# ═══════════════════════════════════════════════════════════════
class Debugger(bdb.Bdb):
    def __init__(self, app):
        super().__init__()
        self.app   = app
        self._wait = threading.Event()
        self._dead = False
        self._cmd  = "step"
        self.frame = None
        self.file  = None
        self.line  = None
        # FIX: store the canonical debug filename so we can match BPs
        self._debug_filename = None

    # FIX: Override canonic() to return our special filename unchanged.
    # bdb.canonic() calls os.path.abspath() which mangles "<untitled>" etc.
    def canonic(self, filename):
        if self._debug_filename and filename == self._debug_filename:
            return filename
        # For real files, use the standard canonic behaviour
        if filename.startswith('<') and filename.endswith('>'):
            return filename
        return super().canonic(filename)

    def user_line(self, frame):
        if self._dead: self.set_quit(); return
        self.frame = frame
        self.file  = frame.f_code.co_filename
        self.line  = frame.f_lineno
        self.app.after(0, self.app.dbg_paused,
                       self.file, self.line,
                       dict(frame.f_locals),
                       self._callstack(frame))
        self._wait.clear()
        self._wait.wait()
        if self._dead: self.set_quit()

    def user_call(self, frame, arg):
        """Called when a function is entered during step-into."""
        if self._dead: self.set_quit(); return

    def user_return(self, frame, return_value):
        """Called when a function returns during step-out."""
        if self._dead: self.set_quit(); return
        self.frame = frame
        self.file  = frame.f_code.co_filename
        self.line  = frame.f_lineno
        self.app.after(0, self.app.dbg_paused,
                       self.file, self.line,
                       dict(frame.f_locals),
                       self._callstack(frame))
        self._wait.clear()
        self._wait.wait()
        if self._dead: self.set_quit()

    def user_exception(self, frame, exc_info):
        msg = "".join(traceback.format_exception(*exc_info))
        self.app.after(0, self.app.log, f"\n[EXCEPTION]\n{msg}\n", "err")
        self._dead = True
        self.set_quit()

    def _callstack(self, frame):
        frames = []
        f = frame
        while f:
            frames.append((f.f_code.co_filename, f.f_lineno, f.f_code.co_name))
            f = f.f_back
        return frames

    def cmd_continue(self): self.set_continue();         self._wait.set()
    def cmd_next(self):     self.set_next(self.frame);   self._wait.set()
    def cmd_step(self):     self.set_step();             self._wait.set()
    def cmd_return(self):   self.set_return(self.frame); self._wait.set()
    def cmd_stop(self):
        self._dead = True; self.set_quit(); self._wait.set()

    # FIX: execute() now accepts the canonical filename explicitly,
    # so compile() and set_break() use the exact same string.
    def execute(self, source, filename):
        self._dead = False
        self._debug_filename = filename
        code = compile(source, filename, "exec")
        globs = {"__name__": "__main__", "__file__": filename}
        try:    self.run(code, globs)
        except bdb.BdbQuit: pass
        except Exception:
            self.app.after(0, self.app.log,
                           f"\n[ERROR]\n{traceback.format_exc()}\n", "err")
        self.app.after(0, self.app.dbg_done)

class Redirect:
    def __init__(self, cb, tag=None): self._cb = cb; self._tag = tag
    def write(self, s):
        if s: self._cb(s, self._tag)
    def flush(self): pass

# ═══════════════════════════════════════════════════════════════
#  DEFAULT CODE SAMPLES
# ═══════════════════════════════════════════════════════════════
DEFAULT_CODE = '''\
# Welcome to Topdebug v2.0
# Set breakpoints (click gutter or F9), then press F5 to debug.
# Try: Ctrl+Space for autocomplete, Ctrl+/ to toggle comment,
#       Ctrl+D to duplicate line, Ctrl+G to jump to line.

def greet(name: str) -> str:
    """Return a personalised greeting."""
    message = f"Hello, {name}!"
    return message

def calculate(a: float, b: float):
    """Perform basic arithmetic."""
    total   = a + b
    product = a * b
    ratio   = a / b if b != 0 else None
    return total, product, ratio

class Counter:
    """A simple counter with history."""
    def __init__(self, start: int = 0):
        self.value   = start
        self.history = []

    def increment(self, step: int = 1):
        self.value += step
        self.history.append(self.value)

    def reset(self):
        self.value = 0
        self.history.clear()

# ── main ──────────────────────────────────────────────────────
names = ["Alice", "Bob", "Charlie"]
for name in names:
    print(greet(name))

t, p, r = calculate(10, 4)
print(f"Total={t}, Product={p}, Ratio={r}")

c = Counter(10)
for i in range(5):
    c.increment(i)
print(f"Counter: {c.value}, history: {c.history}")

squares = [n ** 2 for n in range(1, 8)]
print(f"Squares: {squares}")
'''

DEFAULT_CPP_CODE = '''\
// OpenGL Hello Triangle — C++ example
#include <iostream>
#include <GL/glew.h>
#include <GLFW/glfw3.h>

const char* vertexShaderSrc = R"(
    #version 330 core
    layout(location = 0) in vec3 aPos;
    void main() {
        gl_Position = vec4(aPos, 1.0);
    }
)";

const char* fragmentShaderSrc = R"(
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
    return shader;
}

int main() {
    glfwInit();
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

    GLFWwindow* window = glfwCreateWindow(800, 600, "Hello Triangle", nullptr, nullptr);
    if (!window) { std::cerr << "GLFW window failed" << std::endl; glfwTerminate(); return -1; }
    glfwMakeContextCurrent(window);
    glewExperimental = GL_TRUE;
    glewInit();

    float vertices[] = { -0.5f, -0.5f, 0.0f,  0.5f, -0.5f, 0.0f,  0.0f, 0.5f, 0.0f };
    GLuint VAO, VBO;
    glGenVertexArrays(1, &VAO); glBindVertexArray(VAO);
    glGenBuffers(1, &VBO); glBindBuffer(GL_ARRAY_BUFFER, VBO);
    glBufferData(GL_ARRAY_BUFFER, sizeof(vertices), vertices, GL_STATIC_DRAW);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3*sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);

    GLuint vs   = compileShader(GL_VERTEX_SHADER, vertexShaderSrc);
    GLuint fs   = compileShader(GL_FRAGMENT_SHADER, fragmentShaderSrc);
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

DEFAULT_GLSL_CODE = '''\
// GLSL Fragment Shader
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
    vec2 uv = (TexCoord * 2.0 - 1.0) * vec2(uResolution.x / uResolution.y, 1.0);
    float d    = circleSDF(uv, 0.5 + 0.1 * sin(uTime));
    float ring = smoothstep(0.02, 0.0, abs(d));
    vec3 color = mix(vec3(0.1, 0.1, 0.2), vec3(0.0, 0.8, 1.0), ring);
    FragColor  = vec4(color, 1.0);
}
'''

# ═══════════════════════════════════════════════════════════════
#  AUTOCOMPLETE POPUP
# ═══════════════════════════════════════════════════════════════
class AutocompletePopup:
    KIND_ICON = {
        "keyword": "🔵", "builtin": "🟢", "def": "🔧",
        "class": "🏛", "var": "📦", "method": "🔧",
        "attr": "📌", "snippet": "✨",
    }
    KIND_COLOR = {
        "keyword": "#ff7b72", "builtin": "#79c0ff", "def": "#d2a8ff",
        "class": "#ffa657",   "var": "#e6edf3",     "method": "#d2a8ff",
        "attr": "#79c0ff",    "snippet": "#f0883e",
    }

    def __init__(self, master):
        self.win = None
        self.lb  = None
        self.master = master
        self._items = []
        self._on_select = None

    def show(self, x, y, items, on_select):
        self._items = items
        self._on_select = on_select
        if not items:
            self.hide(); return
        if self.win and self.win.winfo_exists():
            self.win.destroy()
        self.win = tk.Toplevel(self.master)
        self.win.wm_overrideredirect(True)
        self.win.wm_geometry(f"+{x}+{y}")
        self.win.configure(bg=C["border"])
        self.win.lift()
        frame = tk.Frame(self.win, bg=C["ac_popup_bg"], bd=1, relief="flat")
        frame.pack(padx=1, pady=1)
        sb = tk.Scrollbar(frame, orient="vertical", width=10, bg=C["bg_toolbar"])
        self.lb = tk.Listbox(frame, yscrollcommand=sb.set,
            bg=C["ac_popup_bg"], fg=C["ac_popup_fg"],
            selectbackground=C["ac_popup_sel"],
            selectforeground="#ffffff",
            font=MONO_S, borderwidth=0, highlightthickness=0,
            activestyle="none",
            width=36, height=min(12, len(items)))
        sb.config(command=self.lb.yview)
        self.lb.pack(side="left")
        if len(items) > 12: sb.pack(side="right", fill="y")
        for name, kind, extra in items:
            icon = self.KIND_ICON.get(kind, "·")
            label = f" {icon} {name}"
            if extra: label += f"  [{extra}]"
            self.lb.insert("end", label)
        if items:
            self.lb.selection_set(0)
            self.lb.activate(0)
        self.lb.bind("<Return>",        lambda e: self._commit())
        self.lb.bind("<Tab>",           lambda e: self._commit())
        self.lb.bind("<Double-Button-1>",lambda e: self._commit())
        self.lb.bind("<Escape>",        lambda e: self.hide())
        self.lb.focus_set()

    def _commit(self):
        sel = self.lb.curselection()
        if sel and self._on_select:
            idx = sel[0]
            name = self._items[idx][0]
            self._on_select(name)
        self.hide()

    def navigate(self, direction):
        if not self.win or not self.win.winfo_exists(): return
        sel = self.lb.curselection()
        cur = sel[0] if sel else -1
        nxt = max(0, min(len(self._items)-1, cur + direction))
        self.lb.selection_clear(0, "end")
        self.lb.selection_set(nxt)
        self.lb.activate(nxt)
        self.lb.see(nxt)

    def is_visible(self):
        return bool(self.win and self.win.winfo_exists())

    def hide(self):
        if self.win and self.win.winfo_exists():
            self.win.destroy()
        self.win = None

# ═══════════════════════════════════════════════════════════════
#  EDITOR TAB STATE
# ═══════════════════════════════════════════════════════════════
class EditorTab:
    def __init__(self, path=None, content="", lang="python"):
        self.path     = path
        self.content  = content
        self.lang     = lang
        self.bps      = set()
        self.modified = False
        self.saved_hash = hash(content)

    @property
    def name(self):
        if self.path: return os.path.basename(self.path)
        return "untitled.py"

    @property
    def display_name(self):
        return ("● " if self.modified else "") + self.name

    # FIX: Each unsaved tab gets a stable unique debug filename so that
    # compile() and set_break() always use the same string.
    _counter = 0
    @property
    def debug_filename(self):
        """Return the canonical filename to use for compile() and set_break()."""
        if self.path:
            return os.path.abspath(self.path)
        # Unsaved file: use a stable synthetic name like <untitled_1>
        if not hasattr(self, '_debug_id'):
            EditorTab._counter += 1
            self._debug_id = EditorTab._counter
        return f"<untitled_{self._debug_id}>"

# ═══════════════════════════════════════════════════════════════
#  MAIN IDE APPLICATION
# ═══════════════════════════════════════════════════════════════
class IDE(tk.Tk):
    def __init__(self):
        super().__init__()
        self._settings = load_settings()
        theme_name = self._settings.get("theme", "Dark (VS2026)")
        self._apply_theme(theme_name, redraw=False)

        self.title("Topdebug v2.0")
        geom = self._settings.get("geometry", "1500x920")
        self.geometry(geom)
        self.minsize(900, 600)
        self.configure(bg=C["bg"])

        self._tabs: list[EditorTab] = []
        self._active_tab_idx = -1
        self._dbg        = None
        self._running    = False
        self._dbg_line   = None
        self._watches    = []
        self._dbg_locals = {}
        self._find_win   = None
        self._ac_popup   = None
        self._repl_hist  = deque(maxlen=200)
        self._repl_hidx  = -1
        self._repl_interp = _code_mod.InteractiveInterpreter()
        self._completer  = Completer()
        self._last_src   = ""
        self._minimap_job = None
        self._clock_job  = None
        self._recent_files = self._settings.get("recent_files", [])
        self._current_theme_name = theme_name

        self._setup_style()
        self._build_menu()
        self._build_toolbar()
        self._build_layout()
        self._build_statusbar()

        tab = EditorTab(content=DEFAULT_CODE, lang="python")
        self._tabs.append(tab)
        self._render_tabs()
        self._switch_tab(0)

        self.bind("<Configure>", self._on_configure)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._start_clock()

    # ─────────────────────────────────────────────────────────
    #  THEME
    # ─────────────────────────────────────────────────────────
    def _apply_theme(self, name, redraw=True):
        global C
        if name not in THEMES: name = "Dark (VS2026)"
        self._current_theme_name = name
        C.clear()
        C.update(THEMES[name])
        if redraw:
            self._settings["theme"] = name
            save_settings(self._settings)
            messagebox.showinfo("Theme", f"Theme '{name}' applied.\nRestart for full effect.")

    # ─────────────────────────────────────────────────────────
    #  TTK STYLE
    # ─────────────────────────────────────────────────────────
    def _setup_style(self):
        s = ttk.Style(self)
        s.theme_use("default")
        s.configure("VS.Treeview",
            background=C["bg_sidebar"], foreground=C["fg"],
            fieldbackground=C["bg_sidebar"], borderwidth=0,
            font=UI, rowheight=22)
        s.configure("VS.Treeview.Heading",
            background=C["bg_toolbar"], foreground=C["fg_dim"],
            font=UI_B, borderwidth=0, relief="flat")
        s.map("VS.Treeview",
            background=[("selected", C["accent"])],
            foreground=[("selected", C["fg_white"])])
        s.configure("VSBot.TNotebook",
            background=C["bg_bottom"], borderwidth=0, tabmargins=[0,0,0,0])
        s.configure("VSBot.TNotebook.Tab",
            background=C["bg_toolbar"], foreground=C["fg_dim"],
            padding=[12, 4], font=UI_B, borderwidth=0)
        s.map("VSBot.TNotebook.Tab",
            background=[("selected", C["bg_bottom"])],
            foreground=[("selected", C["fg"])])
        s.configure("VSLeft.TNotebook",
            background=C["bg_sidebar"], borderwidth=0, tabmargins=[0,0,0,0])
        s.configure("VSLeft.TNotebook.Tab",
            background=C["bg_toolbar"], foreground=C["fg_dim"],
            padding=[10, 3], font=UI_B, borderwidth=0)
        s.map("VSLeft.TNotebook.Tab",
            background=[("selected", C["bg_sidebar"])],
            foreground=[("selected", C["fg"])])
        s.configure("TCombobox",
            fieldbackground=C["bg_sidebar"], background=C["bg_toolbar"],
            foreground=C["fg"], selectbackground=C["bg_select"],
            selectforeground=C["fg_white"], borderwidth=0, relief="flat")
        s.map("TCombobox",
            fieldbackground=[("readonly", C["bg_sidebar"])],
            foreground=[("readonly", C["fg"])])
        self.option_add("*TCombobox*Listbox.background", C["bg_sidebar"])
        self.option_add("*TCombobox*Listbox.foreground", C["fg"])
        self.option_add("*TCombobox*Listbox.selectBackground", C["accent"])
        self.option_add("*TCombobox*Listbox.selectForeground", C["fg_white"])

    # ─────────────────────────────────────────────────────────
    #  MENU
    # ─────────────────────────────────────────────────────────
    def _build_menu(self):
        def mcfg():
            return dict(bg=C["bg_panel"], fg=C["fg"],
                activebackground=C["accent"], activeforeground=C["fg_white"],
                borderwidth=0, relief="flat", font=UI, selectcolor=C["accent"])
        mb = tk.Menu(self, bg=C["bg_menubar"], fg=C["fg_white"],
            activebackground=C["accent"], activeforeground=C["fg_white"],
            borderwidth=0, relief="flat", font=UI)
        self.config(menu=mb)

        fm = tk.Menu(mb, **mcfg(), tearoff=0)
        mb.add_cascade(label="File", menu=fm)
        fm.add_command(label="New Python File       Ctrl+N",  command=self._new)
        fm.add_command(label="New C++ File",                  command=self._new_cpp)
        fm.add_command(label="New GLSL File",                 command=self._new_glsl)
        fm.add_separator()
        fm.add_command(label="Open File…            Ctrl+O",  command=self._open)
        fm.add_command(label="Save                  Ctrl+S",  command=self._save)
        fm.add_command(label="Save As…              Ctrl+Shift+S", command=self._save_as)
        fm.add_command(label="Close Tab             Ctrl+W",  command=self._close_tab)
        fm.add_separator()
        self._recent_menu = tk.Menu(fm, **mcfg(), tearoff=0)
        fm.add_cascade(label="Recent Files", menu=self._recent_menu)
        self._rebuild_recent_menu()
        fm.add_separator()
        fm.add_command(label="Exit                  Alt+F4",  command=self._on_close)

        em = tk.Menu(mb, **mcfg(), tearoff=0)
        mb.add_cascade(label="Edit", menu=em)
        em.add_command(label="Undo                  Ctrl+Z",  command=lambda: self._editor.edit_undo())
        em.add_command(label="Redo                  Ctrl+Y",  command=lambda: self._editor.edit_redo())
        em.add_separator()
        em.add_command(label="Find…                 Ctrl+F",  command=self._find_dialog)
        em.add_command(label="Find & Replace…       Ctrl+H",  command=self._find_replace_dialog)
        em.add_command(label="Go to Line…           Ctrl+G",  command=self._goto_line_dialog)
        em.add_separator()
        em.add_command(label="Toggle Comment        Ctrl+/",  command=self._toggle_comment)
        em.add_command(label="Duplicate Line        Ctrl+D",  command=self._duplicate_line)
        em.add_command(label="Move Line Up          Alt+Up",  command=self._move_line_up)
        em.add_command(label="Move Line Down        Alt+Down",command=self._move_line_down)
        em.add_separator()
        em.add_command(label="Toggle Breakpoint     F9",      command=self._toggle_bp_cursor)
        em.add_command(label="Clear All Breakpoints",         command=self._clear_all_bps)

        vm = tk.Menu(mb, **mcfg(), tearoff=0)
        mb.add_cascade(label="View", menu=vm)
        vm.add_command(label="Command Palette       Ctrl+Shift+P", command=self._command_palette)
        vm.add_separator()
        vm.add_command(label="Refresh Explorer",    command=self._refresh_explorer)
        vm.add_separator()
        theme_menu = tk.Menu(vm, **mcfg(), tearoff=0)
        vm.add_cascade(label="Color Theme", menu=theme_menu)
        for tname in THEMES:
            theme_menu.add_command(label=tname,
                command=lambda n=tname: self._apply_theme(n))

        dm = tk.Menu(mb, **mcfg(), tearoff=0)
        mb.add_cascade(label="Debug", menu=dm)
        dm.add_command(label="Start / Continue      F5",       command=self._run_or_continue)
        dm.add_command(label="Stop                  Shift+F5", command=self._stop)
        dm.add_separator()
        dm.add_command(label="Step Over             F10",      command=self._over)
        dm.add_command(label="Step Into             F11",      command=self._into)
        dm.add_command(label="Step Out              Shift+F11",command=self._out)
        dm.add_separator()
        dm.add_command(label="Toggle Breakpoint     F9",       command=self._toggle_bp_cursor)

        tm = tk.Menu(mb, **mcfg(), tearoff=0)
        mb.add_cascade(label="Tools", menu=tm)
        tm.add_command(label="Add Watch Expression…",  command=self._add_watch_dialog)
        tm.add_command(label="Command Palette…  Ctrl+Shift+P", command=self._command_palette)

        hm = tk.Menu(mb, **mcfg(), tearoff=0)
        mb.add_cascade(label="Help", menu=hm)
        hm.add_command(label="Keyboard Shortcuts",  command=self._shortcuts_dialog)
        hm.add_command(label="About Topdebug",      command=self._about_dialog)

        self.bind_all("<F5>",              lambda e: self._run_or_continue())
        self.bind_all("<F9>",              lambda e: self._toggle_bp_cursor())
        self.bind_all("<F10>",             lambda e: self._over())
        self.bind_all("<F11>",             lambda e: self._into())
        self.bind_all("<Shift-F5>",        lambda e: self._stop())
        self.bind_all("<Shift-F11>",       lambda e: self._out())
        self.bind_all("<Control-n>",       lambda e: self._new())
        self.bind_all("<Control-o>",       lambda e: self._open())
        self.bind_all("<Control-s>",       lambda e: self._save())
        self.bind_all("<Control-S>",       lambda e: self._save_as())
        self.bind_all("<Control-w>",       lambda e: self._close_tab())
        self.bind_all("<Control-f>",       lambda e: self._find_dialog())
        self.bind_all("<Control-h>",       lambda e: self._find_replace_dialog())
        self.bind_all("<Control-g>",       lambda e: self._goto_line_dialog())
        self.bind_all("<Control-slash>",   lambda e: self._toggle_comment())
        self.bind_all("<Control-d>",       lambda e: self._duplicate_line())
        self.bind_all("<Alt-Up>",          lambda e: self._move_line_up())
        self.bind_all("<Alt-Down>",        lambda e: self._move_line_down())
        self.bind_all("<Control-P>",       lambda e: self._command_palette())
        self.bind_all("<Control-space>",   lambda e: self._trigger_autocomplete())

    def _rebuild_recent_menu(self):
        self._recent_menu.delete(0, "end")
        for p in self._recent_files[:10]:
            self._recent_menu.add_command(
                label=os.path.basename(p),
                command=lambda fp=p: self._load_file(fp))
        if not self._recent_files:
            self._recent_menu.add_command(label="(none)", state="disabled")

    # ─────────────────────────────────────────────────────────
    #  TOOLBAR
    # ─────────────────────────────────────────────────────────
    def _build_toolbar(self):
        bar = tk.Frame(self, bg=C["bg_toolbar"], height=40, bd=0)
        bar.pack(side="top", fill="x")
        bar.pack_propagate(False)

        tk.Frame(bar, bg=C["accent"], width=3).pack(side="left", fill="y")

        def tbtn(text, cmd, fg=None, w=None, tooltip=None):
            b = tk.Button(bar, text=text, command=cmd,
                bg=C["bg_toolbar"], fg=fg or C["fg"],
                font=UI_B, relief="flat", borderwidth=0,
                padx=10, pady=6, cursor="hand2",
                activebackground=C["bg_hover"],
                activeforeground=C["fg_white"])
            if w: b.config(width=w)
            b.pack(side="left", padx=1)
            b.bind("<Enter>", lambda e: b.config(bg=C["bg_hover"]))
            b.bind("<Leave>", lambda e: b.config(bg=C["bg_toolbar"]))
            return b

        def sep():
            tk.Frame(bar, bg=C["border"], width=1).pack(side="left", fill="y", pady=5, padx=4)

        self._btn_run  = tbtn("▶  Run / Debug (F5)", self._run_or_continue, fg=C["green"], w=20)
        self._btn_stop = tbtn("■  Stop (⇧F5)",        self._stop,            fg=C["red"])
        sep()
        self._btn_over = tbtn("⤼  Over (F10)",        self._over,            fg=C["cyan"])
        self._btn_into = tbtn("⤵  Into (F11)",        self._into,            fg=C["cyan"])
        self._btn_out  = tbtn("⤴  Out (⇧F11)",        self._out,             fg=C["cyan"])
        sep()
        tbtn("🔍  Find (Ctrl+F)",           self._find_dialog)
        tbtn("⇄  Replace (Ctrl+H)",         self._find_replace_dialog)
        tbtn("⌖  Goto Line (Ctrl+G)",       self._goto_line_dialog)
        sep()
        tbtn("⌨  Palette (Ctrl+⇧+P)",     self._command_palette)

        self._filelbl = tk.Label(bar, text="  untitled.py",
            bg=C["bg_toolbar"], fg=C["fg_dim"],
            font=UI, anchor="w")
        self._filelbl.pack(side="left", padx=10)

        tk.Frame(bar, bg=C["bg_toolbar"]).pack(side="left", expand=True)
        tk.Label(bar, text="Theme:", bg=C["bg_toolbar"], fg=C["fg_dim"], font=UI_S).pack(side="right", padx=(0,4))
        self._theme_var = tk.StringVar(value=self._current_theme_name)
        theme_cb = ttk.Combobox(bar, textvariable=self._theme_var,
            values=list(THEMES.keys()), width=14, state="readonly", font=UI_S)
        theme_cb.pack(side="right", padx=(0, 8), pady=6)
        theme_cb.bind("<<ComboboxSelected>>",
            lambda e: self._apply_theme(self._theme_var.get()))

        self._set_dbg_btns(False)

    # ─────────────────────────────────────────────────────────
    #  LAYOUT
    # ─────────────────────────────────────────────────────────
    def _build_layout(self):
        self._pw_main = tk.PanedWindow(self, orient="horizontal",
            bg=C["border_dark"], sashwidth=5, sashrelief="flat", bd=0,
            sashpad=0)
        self._pw_main.pack(fill="both", expand=True)

        left = tk.Frame(self._pw_main, bg=C["bg_sidebar"], width=230)
        self._pw_main.add(left, minsize=140)

        left_nb = ttk.Notebook(left, style="VSLeft.TNotebook")
        left_nb.pack(fill="both", expand=True)

        exp_frame = tk.Frame(left_nb, bg=C["bg_sidebar"])
        left_nb.add(exp_frame, text=" 📁 Explorer ")
        self._build_explorer(exp_frame)

        outline_frame = tk.Frame(left_nb, bg=C["bg_sidebar"])
        left_nb.add(outline_frame, text=" ⎇ Outline ")
        self._build_outline_panel(outline_frame)

        dbg_frame = tk.Frame(left_nb, bg=C["bg_sidebar"])
        left_nb.add(dbg_frame, text=" 🔍 Debug ")
        self._build_debug_panels(dbg_frame)

        centre = tk.PanedWindow(self._pw_main, orient="vertical",
            bg=C["border_dark"], sashwidth=5, sashrelief="flat", bd=0)
        self._pw_main.add(centre, minsize=400)

        ed_outer = tk.Frame(centre, bg=C["bg"])
        centre.add(ed_outer, minsize=200)
        self._build_editor_area(ed_outer)

        bot_frame = tk.Frame(centre, bg=C["bg_bottom"])
        centre.add(bot_frame, minsize=80, height=180)
        self._build_bottom_panels(bot_frame)

    # ── Explorer ────────────────────────────────────────────
    def _build_explorer(self, parent):
        hdr = tk.Frame(parent, bg=C["bg_toolbar"], height=28)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Frame(hdr, bg=C["accent"], width=3).pack(side="left", fill="y")
        tk.Label(hdr, text="  SOLUTION EXPLORER", bg=C["bg_toolbar"],
            fg=C["fg_dim"], font=UI_S).pack(side="left")
        tk.Button(hdr, text="↻", command=self._refresh_explorer,
            bg=C["bg_toolbar"], fg=C["fg_dim"], font=UI_S,
            relief="flat", bd=0, padx=6, cursor="hand2").pack(side="right")
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x")

        self._explorer = ttk.Treeview(parent, show="tree",
            style="VS.Treeview", selectmode="browse")
        exp_vsb = tk.Scrollbar(parent, orient="vertical",
            command=self._explorer.yview, width=10)
        exp_vsb.pack(side="right", fill="y")
        self._explorer.config(yscrollcommand=exp_vsb.set)
        self._explorer.pack(fill="both", expand=True)
        self._explorer.bind("<Double-Button-1>", self._explorer_open)
        self._refresh_explorer()

    # ── Symbol Outline ──────────────────────────────────────
    def _build_outline_panel(self, parent):
        hdr = tk.Frame(parent, bg=C["bg_toolbar"], height=28)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Frame(hdr, bg=C["accent"], width=3).pack(side="left", fill="y")
        tk.Label(hdr, text="  SYMBOL OUTLINE", bg=C["bg_toolbar"],
            fg=C["fg_dim"], font=UI_S).pack(side="left")
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x")

        self._outline_tree = ttk.Treeview(parent,
            columns=("line",), show="tree headings",
            style="VS.Treeview", selectmode="browse", height=20)
        self._outline_tree.heading("line", text="Line")
        self._outline_tree.column("#0",   width=150, stretch=True)
        self._outline_tree.column("line", width=40,  stretch=False)
        ov = tk.Scrollbar(parent, orient="vertical",
            command=self._outline_tree.yview, width=10)
        ov.pack(side="right", fill="y")
        self._outline_tree.config(yscrollcommand=ov.set)
        self._outline_tree.pack(fill="both", expand=True)
        self._outline_tree.bind("<Double-Button-1>", self._outline_jump)

    def _refresh_outline(self):
        self._outline_tree.delete(*self._outline_tree.get_children())
        src = self._editor.get("1.0", "end-1c")
        outline = build_outline(src)
        nodes = {}
        for lineno, indent, kind, name in outline:
            icon = "🏛" if kind == "class" else "🔧"
            label = f"{icon} {name}"
            parent_id = ""
            for pid, (pi, pk) in nodes.items():
                if pi < indent and pk == "class":
                    parent_id = pid
            iid = self._outline_tree.insert(parent_id, "end",
                text=label, values=(str(lineno),))
            nodes[iid] = (indent, kind)

    def _outline_jump(self, e):
        sel = self._outline_tree.selection()
        if sel:
            vals = self._outline_tree.item(sel[0], "values")
            if vals:
                ln = int(vals[0])
                self._editor.see(f"{ln}.0")
                self._editor.mark_set("insert", f"{ln}.0")
                self._editor.focus_set()

    # ── Debug sub-panels ────────────────────────────────────
    def _build_debug_panels(self, parent):
        dbg_nb = ttk.Notebook(parent, style="VSLeft.TNotebook")
        dbg_nb.pack(fill="both", expand=True)

        vars_f = tk.Frame(dbg_nb, bg=C["bg_panel"])
        dbg_nb.add(vars_f, text=" Locals ")
        self._vars_tree = self._make_tree(vars_f, ("Name", "Value", "Type"))

        watch_f = tk.Frame(dbg_nb, bg=C["bg_panel"])
        dbg_nb.add(watch_f, text=" Watch ")
        self._build_watch_panel(watch_f)

        stack_f = tk.Frame(dbg_nb, bg=C["bg_panel"])
        dbg_nb.add(stack_f, text=" Call Stack ")
        self._stack_tree = self._make_tree(stack_f, ("Function", "File", "Line"))

    # ─────────────────────────────────────────────────────────
    #  EDITOR AREA
    # ─────────────────────────────────────────────────────────
    def _build_editor_area(self, parent):
        self._tab_bar = tk.Frame(parent, bg=C["bg_tab_bar"], height=34)
        self._tab_bar.pack(fill="x")
        self._tab_bar.pack_propagate(False)
        self._tab_buttons = []

        self._breadcrumb_bar = tk.Frame(parent, bg=C["bg_toolbar"], height=24)
        self._breadcrumb_bar.pack(fill="x")
        self._breadcrumb_bar.pack_propagate(False)
        tk.Frame(parent, bg=C["border"], height=1).pack(fill="x")
        self._breadcrumb_lbl = tk.Label(self._breadcrumb_bar,
            text="  …", bg=C["bg_toolbar"], fg=C["fg_dim"], font=UI_S, anchor="w")
        self._breadcrumb_lbl.pack(fill="x", padx=4)

        row = tk.Frame(parent, bg=C["bg"])
        row.pack(fill="both", expand=True)

        self._gutter = tk.Canvas(row, width=62, bg=C["gutter_bg"],
            highlightthickness=0, cursor="arrow")
        self._gutter.pack(side="left", fill="y")
        self._gutter.bind("<Button-1>", self._gutter_click)
        tk.Frame(row, bg=C["border"], width=1).pack(side="left", fill="y")

        ef = tk.Frame(row, bg=C["bg"])
        ef.pack(side="left", fill="both", expand=True)

        self._editor = tk.Text(ef,
            bg=C["bg"], fg=C["fg"],
            insertbackground=C["accent2"],
            insertwidth=2,
            selectbackground=C["bg_select"],
            selectforeground=C["fg_white"],
            font=MONO, wrap="none",
            borderwidth=0, relief="flat",
            undo=True, autoseparators=True,
            tabs=("28",),
            spacing1=2, spacing3=2,
            padx=6)
        self._editor.pack(fill="both", expand=True, side="left")

        vsb = tk.Scrollbar(ef, orient="vertical",
            command=self._editor.yview,
            bg=C["bg_toolbar"], troughcolor=C["bg_panel"], width=12)
        vsb.pack(side="right", fill="y")
        self._editor.config(yscrollcommand=lambda *a: (vsb.set(*a), self._sync_gutter()))

        hsb = tk.Scrollbar(parent, orient="horizontal",
            command=self._editor.xview,
            bg=C["bg_toolbar"], troughcolor=C["bg_panel"], width=12)
        hsb.pack(fill="x")
        self._editor.config(xscrollcommand=hsb.set)

        tk.Frame(row, bg=C["border"], width=1).pack(side="left", fill="y")
        self._minimap = tk.Canvas(row, width=80, bg=C["minimap_bg"],
            highlightthickness=0, cursor="hand2")
        self._minimap.pack(side="left", fill="y")
        self._minimap.bind("<Button-1>",  self._minimap_click)
        self._minimap.bind("<B1-Motion>", self._minimap_click)

        self._ac_popup = AutocompletePopup(self)

        self._editor.bind("<KeyRelease>",     self._on_key)
        self._editor.bind("<Return>",         self._auto_indent, add="+")
        self._editor.bind("<Tab>",            self._insert_tab)
        self._editor.bind("<Shift-Tab>",      self._unindent_selection)
        self._editor.bind("<ButtonRelease>",  self._on_click)
        self._editor.bind("<MouseWheel>",     lambda e: self.after(10, self._sync_gutter))
        self._editor.bind("<Button-4>",       lambda e: self.after(10, self._sync_gutter))
        self._editor.bind("<Button-5>",       lambda e: self.after(10, self._sync_gutter))
        self._editor.bind("<Up>",             self._on_up)
        self._editor.bind("<Down>",           self._on_down)
        self._editor.bind("<Escape>",         lambda e: self._ac_popup.hide())
        self._editor.bind("<KeyRelease>",     self._match_brackets, add="+")
        for opener, closer in (("(",")"),(  "[","]"),("{","}"),("'","'"),('\"','\"')):
            self._editor.bind(opener,
                lambda e, c=closer: self._auto_close(e, c), add="+")

    # ─────────────────────────────────────────────────────────
    #  MULTI-TAB MANAGEMENT
    # ─────────────────────────────────────────────────────────
    def _render_tabs(self):
        for btn in self._tab_buttons:
            btn.destroy()
        self._tab_buttons.clear()

        for i, tab in enumerate(self._tabs):
            is_active = (i == self._active_tab_idx)
            bg = C["bg_tab_act"] if is_active else C["bg_tab"]
            fg = C["fg_tab_act"] if is_active else C["fg_tab"]

            btn_frame = tk.Frame(self._tab_bar, bg=bg)
            btn_frame.pack(side="left")

            if is_active:
                tk.Frame(btn_frame, bg=C["accent"], height=2).pack(fill="x", side="top")

            lbl = tk.Label(btn_frame, text=f"  {tab.display_name}  ",
                bg=bg, fg=fg, font=UI, padx=2, pady=5, cursor="hand2")
            lbl.pack(side="left")

            close_btn = tk.Label(btn_frame, text=" ×",
                bg=bg, fg=C["fg_dim"], font=UI, cursor="hand2")
            close_btn.pack(side="left", pady=5)

            lbl.bind("<Button-1>",       lambda e, idx=i: self._switch_tab(idx))
            btn_frame.bind("<Button-1>", lambda e, idx=i: self._switch_tab(idx))
            close_btn.bind("<Button-1>", lambda e, idx=i: self._close_tab(idx))

            self._tab_buttons.append(btn_frame)

        plus = tk.Label(self._tab_bar, text="  +  ",
            bg=C["bg_tab_bar"], fg=C["fg_dim"], font=UI, cursor="hand2")
        plus.pack(side="left")
        plus.bind("<Button-1>", lambda e: self._new())
        self._tab_buttons.append(plus)

    def _switch_tab(self, idx):
        if idx < 0 or idx >= len(self._tabs): return

        # FIX: Save current editor content AND breakpoints to the current tab
        # before switching away.
        if self._active_tab_idx >= 0 and self._active_tab_idx < len(self._tabs):
            old_tab = self._tabs[self._active_tab_idx]
            old_tab.content = self._editor.get("1.0", "end-1c")
            old_tab.bps     = self._bps_for_active()

        self._active_tab_idx = idx
        tab = self._tabs[idx]

        # Load content into editor
        self._editor.delete("1.0", "end")
        self._editor.insert("1.0", tab.content)
        self._editor.edit_reset()

        # FIX: Restore breakpoints by reapplying tags from tab.bps
        # (tags were wiped by delete() above, so we must re-add them)
        self._editor.tag_remove("bp_ln", "1.0", "end")
        for ln in tab.bps:
            self._editor.tag_add("bp_ln", f"{ln}.0", f"{ln+1}.0")

        self._apply_language_setup_for(tab)
        self._render_tabs()
        self._update_filelbl(tab)
        self._sync_gutter()
        self._refresh_outline()
        self._update_breadcrumb()
        self._schedule_minimap()

    def _bps_for_active(self):
        """Read breakpoint line numbers from the editor's bp_ln tags."""
        bps = set()
        total = int(self._editor.index("end").split(".")[0])
        for ln in range(1, total + 1):
            tags = self._editor.tag_names(f"{ln}.0")
            if "bp_ln" in tags:
                bps.add(ln)
        return bps

    def _close_tab(self, idx=None):
        if idx is None:
            idx = self._active_tab_idx
        if idx < 0 or idx >= len(self._tabs): return
        tab = self._tabs[idx]
        if tab.modified:
            ans = messagebox.askyesnocancel("Unsaved Changes",
                f"Save '{tab.name}' before closing?")
            if ans is None: return
            if ans: self._save()
        self._tabs.pop(idx)
        if not self._tabs:
            new_tab = EditorTab(content=DEFAULT_CODE, lang="python")
            self._tabs.append(new_tab)
        new_idx = max(0, min(idx, len(self._tabs)-1))
        self._active_tab_idx = -1
        self._render_tabs()
        self._switch_tab(new_idx)

    def _active_tab(self):
        if 0 <= self._active_tab_idx < len(self._tabs):
            return self._tabs[self._active_tab_idx]
        return None

    def _update_filelbl(self, tab):
        self._filelbl.config(text=f"  {tab.path or 'untitled'}")
        name = tab.path or "untitled.py"
        self.title(f"Topdebug v2.0 — {name}")

    # ─────────────────────────────────────────────────────────
    #  BOTTOM PANELS
    # ─────────────────────────────────────────────────────────
    def _build_bottom_panels(self, parent):
        bot_nb = ttk.Notebook(parent, style="VSBot.TNotebook")
        bot_nb.pack(fill="both", expand=True)

        out_f = tk.Frame(bot_nb, bg=C["bg_bottom"])
        bot_nb.add(out_f, text=" Output ")
        self._build_output(out_f)

        err_f = tk.Frame(bot_nb, bg=C["bg_bottom"])
        bot_nb.add(err_f, text=" Error List ")
        self._build_error_list(err_f)

        con_f = tk.Frame(bot_nb, bg=C["bg_bottom"])
        bot_nb.add(con_f, text=" Python Interactive ")
        self._build_console(con_f)

        mem_f = tk.Frame(bot_nb, bg=C["bg_bottom"])
        bot_nb.add(mem_f, text=" Memory ")
        self._build_memory_view(mem_f)

    def _build_output(self, parent):
        hdr = tk.Frame(parent, bg=C["bg_bottom"])
        hdr.pack(fill="x", pady=2, padx=4)
        tk.Label(hdr, text="Show output from:", bg=C["bg_bottom"],
            fg=C["fg_dim"], font=UI).pack(side="left")
        src_var = tk.StringVar(value="Debug")
        ttk.Combobox(hdr, textvariable=src_var,
            values=["Build","Debug","Python Output"], width=14,
            state="readonly", font=UI).pack(side="left", padx=6)
        tk.Button(hdr, text="✕ Clear", command=self._clear_output,
            bg=C["bg_toolbar"], fg=C["fg_dim"], font=UI_S,
            relief="flat", bd=0, padx=6, cursor="hand2").pack(side="right")

        self._out = tk.Text(parent,
            bg=C["bg"], fg=C["fg"],
            font=MONO_S, borderwidth=0, relief="flat",
            state="disabled", wrap="word")
        self._out.pack(fill="both", expand=True, side="left")
        self._out.tag_config("err",  foreground=C["red"])
        self._out.tag_config("info", foreground=C["cyan"])
        self._out.tag_config("ok",   foreground=C["green"])
        self._out.tag_config("warn", foreground=C["orange"])
        vsb = tk.Scrollbar(parent, orient="vertical",
            command=self._out.yview, width=12)
        vsb.pack(side="right", fill="y")
        self._out.config(yscrollcommand=vsb.set)

    def _clear_output(self):
        self._out.config(state="normal")
        self._out.delete("1.0", "end")
        self._out.config(state="disabled")

    def _build_error_list(self, parent):
        bar = tk.Frame(parent, bg=C["bg_bottom"])
        bar.pack(fill="x", padx=4, pady=3)
        self._err_count_lbl = tk.Label(bar,
            text="⊘ 0 Errors   ⚠ 0 Warnings   ℹ 0 Messages",
            bg=C["bg_bottom"], fg=C["fg_dim"], font=UI)
        self._err_count_lbl.pack(side="left")
        tk.Button(bar, text="✕ Clear", command=self._clear_errors,
            bg=C["bg_toolbar"], fg=C["fg_dim"], font=UI_S,
            relief="flat", bd=0, padx=6, cursor="hand2").pack(side="right")

        self._err_tree = ttk.Treeview(parent,
            columns=("code","desc","file","line","col"),
            show="headings", style="VS.Treeview",
            selectmode="browse", height=5)
        for col, w, lbl in [
            ("code",50,"Code"),("desc",340,"Description"),
            ("file",100,"File"),("line",45,"Line"),("col",45,"Col")]:
            self._err_tree.heading(col, text=lbl)
            self._err_tree.column(col, width=w, stretch=(col=="desc"))
        self._err_tree.bind("<Double-Button-1>", self._err_jump)
        vsb2 = tk.Scrollbar(parent, orient="vertical",
            command=self._err_tree.yview, width=12)
        vsb2.pack(side="right", fill="y")
        self._err_tree.config(yscrollcommand=vsb2.set)
        self._err_tree.pack(fill="both", expand=True)

    def _err_jump(self, e):
        sel = self._err_tree.selection()
        if sel:
            vals = self._err_tree.item(sel[0], "values")
            if vals and len(vals) >= 4:
                try:
                    ln = int(vals[3])
                    self._editor.see(f"{ln}.0")
                    self._editor.mark_set("insert", f"{ln}.0")
                    self._editor.focus_set()
                except Exception: pass

    def _build_console(self, parent):
        self._con_out = tk.Text(parent,
            bg=C["bg"], fg=C["fg"],
            font=MONO_S, borderwidth=0, relief="flat",
            state="disabled", wrap="word")
        self._con_out.pack(fill="both", expand=True)
        self._con_out.tag_config("err",   foreground=C["red"])
        self._con_out.tag_config("info",  foreground=C["cyan"])
        self._con_out.tag_config("prompt",foreground=C["s_fn"])

        inp_row = tk.Frame(parent, bg=C["bg_toolbar"])
        inp_row.pack(fill="x")
        tk.Label(inp_row, text=">>> ", bg=C["bg_toolbar"],
            fg=C["s_fn"], font=MONO_S).pack(side="left", padx=4)
        self._con_in = tk.Entry(inp_row,
            bg=C["bg"], fg=C["fg"],
            insertbackground=C["fg"],
            font=MONO_S, relief="flat", borderwidth=0,
            highlightthickness=1, highlightbackground=C["border"])
        self._con_in.pack(fill="x", expand=True, side="left", ipady=4, padx=(0,4), pady=3)
        self._con_in.bind("<Return>",  self._repl_exec)
        self._con_in.bind("<Up>",      self._repl_hist_up)
        self._con_in.bind("<Down>",    self._repl_hist_down)
        tk.Button(inp_row, text="Clear", command=self._repl_clear,
            bg=C["bg_toolbar"], fg=C["fg_dim"], font=UI_S,
            relief="flat", bd=0, padx=8, cursor="hand2").pack(side="right", padx=4)
        self._con_out_write("Python Interactive Console — Ctrl+Space for help\n", "info")

    # ─────────────────────────────────────────────────────────
    #  MEMORY VIEW  (VS 2026-style hex editor panel)
    # ─────────────────────────────────────────────────────────
    def _build_memory_view(self, parent):
        import ctypes, struct

        # ── toolbar ──────────────────────────────────────────
        tb = tk.Frame(parent, bg=C["bg_toolbar"], height=30)
        tb.pack(fill="x")
        tb.pack_propagate(False)

        tk.Label(tb, text=" Address:", bg=C["bg_toolbar"],
                 fg=C["fg_dim"], font=UI).pack(side="left", padx=(6,2))

        self._mem_addr_var = tk.StringVar(value="0x00000000")
        addr_entry = tk.Entry(tb, textvariable=self._mem_addr_var,
            bg=C["bg"], fg=C["cyan"], insertbackground=C["cyan"],
            font=("Consolas", 9), relief="solid", bd=1, width=20,
            highlightthickness=1, highlightbackground=C["accent"])
        addr_entry.pack(side="left", ipady=2, padx=2)

        tk.Button(tb, text="Go", command=self._mem_go,
            bg=C["accent"], fg=C["fg_white"], font=UI_S,
            relief="flat", bd=0, padx=10, pady=2,
            cursor="hand2").pack(side="left", padx=4)

        # quick-pick: inspect a live Python variable by name
        tk.Label(tb, text="  Inspect var:", bg=C["bg_toolbar"],
                 fg=C["fg_dim"], font=UI).pack(side="left", padx=(10,2))
        self._mem_var_entry = tk.Entry(tb,
            bg=C["bg"], fg=C["s_fn"], insertbackground=C["s_fn"],
            font=("Consolas", 9), relief="solid", bd=1, width=14,
            highlightthickness=1, highlightbackground=C["accent"])
        self._mem_var_entry.pack(side="left", ipady=2, padx=2)
        tk.Button(tb, text="Inspect", command=self._mem_inspect_var,
            bg=C["bg_toolbar"], fg=C["fg"], font=UI_S,
            relief="flat", bd=0, padx=10, pady=2,
            cursor="hand2").pack(side="left", padx=2)

        # bytes-per-row selector
        tk.Label(tb, text="  Columns:", bg=C["bg_toolbar"],
                 fg=C["fg_dim"], font=UI).pack(side="left", padx=(10,2))
        self._mem_cols_var = tk.StringVar(value="16")
        cols_cb = ttk.Combobox(tb, textvariable=self._mem_cols_var,
            values=["8","16","32"], width=4, state="readonly", font=UI_S)
        cols_cb.pack(side="left", padx=2)
        cols_cb.bind("<<ComboboxSelected>>", lambda e: self._mem_refresh())

        tk.Button(tb, text="↻ Refresh", command=self._mem_refresh,
            bg=C["bg_toolbar"], fg=C["fg_dim"], font=UI_S,
            relief="flat", bd=0, padx=8, pady=2,
            cursor="hand2").pack(side="right", padx=6)

        # ── column headers ───────────────────────────────────
        hdr_frame = tk.Frame(parent, bg=C["bg_panel"])
        hdr_frame.pack(fill="x")
        self._mem_hdr = tk.Text(hdr_frame,
            bg=C["bg_panel"], fg=C["fg_dim"],
            font=("Consolas", 9), height=1, relief="flat",
            borderwidth=0, state="disabled", wrap="none",
            highlightthickness=0)
        self._mem_hdr.pack(fill="x", padx=0)

        # ── main hex display (3 panes: address | hex | ascii) ─
        body = tk.Frame(parent, bg=C["bg"])
        body.pack(fill="both", expand=True)

        self._mem_text = tk.Text(body,
            bg=C["bg"], fg=C["fg"],
            font=("Consolas", 9), relief="flat",
            borderwidth=0, state="disabled", wrap="none",
            highlightthickness=0,
            selectbackground=C["bg_select"],
            selectforeground=C["fg_white"],
            cursor="xterm")
        vsb = tk.Scrollbar(body, orient="vertical",
            command=self._mem_text.yview, width=12,
            bg=C["bg_toolbar"])
        hsb = tk.Scrollbar(body, orient="horizontal",
            command=self._mem_text.xview, width=12,
            bg=C["bg_toolbar"])
        self._mem_text.config(yscrollcommand=vsb.set,
                              xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self._mem_text.pack(fill="both", expand=True)

        # colour tags
        self._mem_text.tag_config("addr",
            foreground=C["s_cmt"])
        self._mem_text.tag_config("sep",
            foreground=C["border"])
        self._mem_text.tag_config("hex_even",
            foreground=C["fg"])
        self._mem_text.tag_config("hex_odd",
            foreground=C["accent2"])
        self._mem_text.tag_config("hex_zero",
            foreground=C["fg_muted"])
        self._mem_text.tag_config("ascii_print",
            foreground=C["s_str"])
        self._mem_text.tag_config("ascii_dot",
            foreground=C["fg_muted"])
        self._mem_text.tag_config("highlight",
            background=C["bg_select"], foreground=C["fg_white"])

        # status bar at bottom
        self._mem_status = tk.Label(parent,
            text="  Ready — enter an address or variable name",
            bg=C["bg_panel"], fg=C["fg_dim"], font=UI_S, anchor="w")
        self._mem_status.pack(fill="x", side="bottom")

        # internal state
        self._mem_bytes   = b""
        self._mem_base    = 0
        self._mem_rows    = 256   # number of rows to show

        self._mem_text.bind("<Button-1>", self._mem_on_click)
        addr_entry.bind("<Return>", lambda e: self._mem_go())
        self._mem_var_entry.bind("<Return>", lambda e: self._mem_inspect_var())

        # draw initial placeholder
        self._mem_draw_placeholder()

    def _mem_draw_placeholder(self):
        cols = int(self._mem_cols_var.get())
        self._mem_update_header(cols)
        self._mem_text.config(state="normal")
        self._mem_text.delete("1.0", "end")
        placeholder = (
            "  ┌─────────────────────────────────────────────────┐\n"
            "  │   VS 2026  Memory View                          │\n"
            "  │                                                  │\n"
            "  │   Enter an address  (e.g.  0x1A2B3C)            │\n"
            "  │   — or —                                        │\n"
            "  │   Type a variable name and click Inspect        │\n"
            "  │   to read live Python object memory.            │\n"
            "  │                                                  │\n"
            "  └─────────────────────────────────────────────────┘\n"
        )
        self._mem_text.insert("1.0", placeholder, "addr")
        self._mem_text.config(state="disabled")

    def _mem_update_header(self, cols):
        offset_w = 10   # "0x00000000 "
        hex_w    = cols * 3
        self._mem_hdr.config(state="normal")
        self._mem_hdr.delete("1.0", "end")
        hdr  = " " * offset_w + "  "
        hdr += "".join(f"{i:02X} " for i in range(cols))
        hdr += "  " + "".join(f"{i%16:X}" for i in range(cols))
        self._mem_hdr.insert("1.0", hdr)
        self._mem_hdr.config(state="disabled")

    def _mem_go(self):
        raw = self._mem_addr_var.get().strip()
        try:
            base = int(raw, 16) if raw.startswith("0x") or raw.startswith("0X") \
                   else int(raw, 0)
        except ValueError:
            self._mem_status.config(
                text=f"  ⊘ Invalid address: {raw}", fg=C["red"])
            return
        self._mem_read_and_show(base)

    def _mem_inspect_var(self):
        name = self._mem_var_entry.get().strip()
        if not name:
            return

        # try locals from the last debug pause first, then REPL globals
        loc = dict(self._dbg_locals) if self._dbg_locals else {}
        repl_globals = self._repl_interp.locals if hasattr(
            self._repl_interp, "locals") else {}
        loc.update(repl_globals)

        if name not in loc:
            # try evaluating as expression
            try:
                val = eval(name, loc)
            except Exception:
                self._mem_status.config(
                    text=f"  ⊘ Variable '{name}' not found",
                    fg=C["red"])
                return
        else:
            val = loc[name]

        addr = id(val)
        self._mem_addr_var.set(f"0x{addr:016X}")
        self._mem_status.config(
            text=f"  ℹ  '{name}'  →  {type(val).__name__}  "
                 f"@ 0x{addr:016X}   size={val.__sizeof__()} bytes",
            fg=C["cyan"])
        self._mem_read_and_show(addr, hint_size=val.__sizeof__())

    def _mem_read_and_show(self, base, hint_size=None):
        import ctypes
        cols      = int(self._mem_cols_var.get())
        read_size = hint_size if hint_size and hint_size > 0 else cols * self._mem_rows
        read_size = max(read_size, cols)
        # round up to a full row
        read_size = ((read_size + cols - 1) // cols) * cols

        try:
            buf = (ctypes.c_uint8 * read_size).from_address(base)
            data = bytes(buf)
        except Exception as ex:
            self._mem_status.config(
                text=f"  ⊘ Cannot read memory at 0x{base:X}: {ex}",
                fg=C["red"])
            self._mem_draw_placeholder()
            return

        self._mem_bytes = data
        self._mem_base  = base
        self._mem_render(cols)
        self._mem_status.config(
            text=f"  ✓  0x{base:016X}  —  {len(data)} bytes read   "
                 f"({cols} columns)",
            fg=C["green"])

    def _mem_render(self, cols):
        data = self._mem_bytes
        base = self._mem_base
        self._mem_update_header(cols)

        self._mem_text.config(state="normal")
        self._mem_text.delete("1.0", "end")

        for row_i in range(0, len(data), cols):
            chunk = data[row_i:row_i + cols]
            addr  = base + row_i

            # address column
            addr_str = f"0x{addr:08X}"
            self._mem_text.insert("end", addr_str, "addr")
            self._mem_text.insert("end", "  ", "sep")

            # hex bytes
            for b_i, b in enumerate(chunk):
                hex_str = f"{b:02X} "
                if b == 0:
                    tag = "hex_zero"
                elif b_i % 2 == 0:
                    tag = "hex_even"
                else:
                    tag = "hex_odd"
                self._mem_text.insert("end", hex_str, tag)

            # padding if last row is short
            pad = cols - len(chunk)
            if pad:
                self._mem_text.insert("end", "   " * pad, "sep")

            # ascii column
            self._mem_text.insert("end", "  ", "sep")
            for b in chunk:
                if 32 <= b < 127:
                    self._mem_text.insert("end", chr(b), "ascii_print")
                else:
                    self._mem_text.insert("end", "·", "ascii_dot")

            self._mem_text.insert("end", "\n")

        self._mem_text.config(state="disabled")

    def _mem_refresh(self):
        if self._mem_bytes:
            cols = int(self._mem_cols_var.get())
            self._mem_render(cols)
        else:
            self._mem_go()

    def _mem_on_click(self, event):
        """Highlight the byte the user clicked on."""
        idx  = self._mem_text.index(f"@{event.x},{event.y}")
        line = int(idx.split(".")[0]) - 1
        col  = int(idx.split(".")[1])
        cols = int(self._mem_cols_var.get())
        # address column width = 10 + 2 gap = 12
        hex_start = 12
        hex_end   = hex_start + cols * 3
        if hex_start <= col < hex_end:
            byte_idx = (col - hex_start) // 3
            abs_idx  = line * cols + byte_idx
            if 0 <= abs_idx < len(self._mem_bytes):
                bval = self._mem_bytes[abs_idx]
                addr = self._mem_base + abs_idx
                self._mem_status.config(
                    text=f"  Address: 0x{addr:016X}   "
                         f"Value: 0x{bval:02X}  ({bval:3d})  "
                         f"'{chr(bval) if 32<=bval<127 else '·'}'",
                    fg=C["yellow"])

    # ─────────────────────────────────────────────────────────
    #  STATUS BAR
    # ─────────────────────────────────────────────────────────
    def _build_statusbar(self):
        sb = tk.Frame(self, bg=C["bg_statusbar"], height=26)
        sb.pack(side="bottom", fill="x")
        sb.pack_propagate(False)

        self._stlbl = tk.Label(sb, text="  ✓  Ready",
            bg=C["bg_statusbar"], fg=C["fg_white"],
            font=("Segoe UI", 8, "bold"), anchor="w")
        self._stlbl.pack(side="left", fill="y")

        tk.Label(sb, text="  F5 Run  ·  F9 BP  ·  F10 Over  ·  F11 Into  ·  Ctrl+Space AC",
            bg=C["bg_statusbar"], fg="#8bbfee", font=UI_S).pack(side="left", padx=6)

        def seg(text, w=None):
            tk.Frame(sb, bg="#0a4080", width=1).pack(side="right", fill="y")
            kw = dict(bg=C["bg_statusbar"], fg=C["fg_white"], font=UI_S, padx=3)
            if w: kw["width"] = w
            lbl = tk.Label(sb, text=f"  {text}  ", **kw)
            lbl.pack(side="right", fill="y")
            return lbl

        self._clock_lbl  = seg("00:00:00", w=10)
        self._enclbl     = seg("UTF-8")
        self._eollbl     = seg("LF")
        self._spacelbl   = seg("Spaces: 4")
        self._poslbl     = seg("Ln 1, Col 1", w=14)
        self._langseg    = seg("Python", w=12)

    def _start_clock(self):
        def tick():
            now = datetime.now().strftime("%H:%M:%S")
            try:
                self._clock_lbl.config(text=f"  {now}  ")
            except Exception:
                return
            self._clock_job = self.after(1000, tick)
        tick()

    # ── FIX: lock editor during debugging to prevent code/line mismatch ──
    def _lock_editor(self):
        self._editor.config(state="disabled")

    def _unlock_editor(self):
        self._editor.config(state="normal")

    def _status(self, msg, color=None):
        color = color or C["bg_statusbar"]
        try:
            self._stlbl.config(text=f"  {msg}", bg=color)
            self._stlbl.master.config(bg=color)
            for child in self._stlbl.master.winfo_children():
                try: child.config(bg=color)
                except: pass
        except Exception:
            pass

    def _update_pos(self, e=None):
        idx = self._editor.index("insert")
        ln, col = idx.split(".")
        try:
            self._poslbl.config(text=f"  Ln {ln}, Col {int(col)+1}  ")
        except Exception:
            pass
        self._update_breadcrumb()

    # ─────────────────────────────────────────────────────────
    #  BREADCRUMB
    # ─────────────────────────────────────────────────────────
    def _update_breadcrumb(self):
        tab = self._active_tab()
        if not tab: return
        fname = tab.name
        src   = self._editor.get("1.0", "end-1c")
        ln    = int(self._editor.index("insert").split(".")[0])
        current_fn = ""
        current_cl = ""
        for lineno, indent, kind, name in build_outline(src):
            if lineno <= ln:
                if kind == "class" and indent == 0: current_cl = name
                if kind == "def":   current_fn = name
        crumb = f"  {fname}"
        if current_cl: crumb += f"  ›  {current_cl}"
        if current_fn: crumb += f"  ›  {current_fn}"
        try:
            self._breadcrumb_lbl.config(text=crumb)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────
    #  GUTTER
    # ─────────────────────────────────────────────────────────
    def _sync_gutter(self, e=None):
        self._gutter.delete("all")
        tab = self._active_tab()
        # FIX: Use tab.bps as the authoritative source; also update it
        # from the editor tags so gutter stays in sync after edits.
        bps = self._bps_for_active()
        if tab:
            tab.bps = bps

        i = self._editor.index("@0,0")
        cur_ln = int(self._editor.index("insert").split(".")[0])
        while True:
            dl = self._editor.dlineinfo(i)
            if dl is None: break
            y, h = dl[1], dl[3]
            cy   = y + h // 2
            ln   = int(i.split(".")[0])

            if ln == cur_ln:
                self._gutter.create_rectangle(0, y, 3, y+h,
                    fill=C["accent2"], outline="")

            if ln in bps:
                self._gutter.create_oval(4, cy-7, 20, cy+7,
                    fill=C["bp_glow"], outline="")
                self._gutter.create_oval(5, cy-6, 19, cy+6,
                    fill=C["bp_red"], outline="#ff6666", width=1)

            if ln == self._dbg_line:
                self._gutter.create_oval(20, cy-6, 36, cy+6,
                    fill=C["arrow_glow"], outline="")
                pts = [22, cy-5, 36, cy, 22, cy+5]
                self._gutter.create_polygon(pts, fill=C["arrow"],
                    outline="#c8a000", width=1)

            self._gutter.create_text(60, cy,
                text=str(ln),
                fill=C["arrow"] if ln == self._dbg_line else
                     (C["gutter_ln"] if ln != cur_ln else C["fg_dim"]),
                anchor="e", font=MONO_S)

            nxt = self._editor.index(f"{i}+1line")
            if nxt == i: break
            i = nxt

    def _gutter_click(self, e):
        idx = self._editor.index(f"@0,{e.y}")
        ln  = int(idx.split(".")[0])
        self._toggle_bp(ln)

    def _toggle_bp(self, ln):
        tab = self._active_tab()
        if tab is None: return
        if ln in tab.bps:
            tab.bps.discard(ln)
            self._editor.tag_remove("bp_ln", f"{ln}.0", f"{ln+1}.0")
        else:
            tab.bps.add(ln)
            self._editor.tag_add("bp_ln", f"{ln}.0", f"{ln+1}.0")
        self._sync_gutter()

    def _toggle_bp_cursor(self):
        ln = int(self._editor.index("insert").split(".")[0])
        self._toggle_bp(ln)

    def _clear_all_bps(self):
        tab = self._active_tab()
        if not tab: return
        for ln in list(tab.bps): self._toggle_bp(ln)

    # ─────────────────────────────────────────────────────────
    #  MINIMAP
    # ─────────────────────────────────────────────────────────
    def _schedule_minimap(self):
        if self._minimap_job:
            self.after_cancel(self._minimap_job)
        self._minimap_job = self.after(400, self._draw_minimap)

    def _draw_minimap(self):
        self._minimap.delete("all")
        w = self._minimap.winfo_width()
        h = self._minimap.winfo_height()
        if w < 5 or h < 5: return
        src = self._editor.get("1.0", "end-1c")
        lines = src.split("\n")
        total = max(len(lines), 1)
        lh = max(1, h / total)

        try:
            y1_frac, y2_frac = map(float, self._editor.yview())
        except Exception:
            y1_frac, y2_frac = 0, 1
        vp_y1 = int(y1_frac * h)
        vp_y2 = int(y2_frac * h)
        self._minimap.create_rectangle(0, vp_y1, w, vp_y2,
            fill=C["bg_hover"], outline="", stipple="")

        for i, line in enumerate(lines):
            y = int(i * lh)
            stripped = line.lstrip()
            indent   = len(line) - len(stripped)
            if not stripped: continue
            color = C["minimap_fg"]
            if stripped.startswith("#") or stripped.startswith("//"):
                color = C["s_cmt"]
            elif re.match(r'(def|class|void|int|float)\b', stripped):
                color = C["s_fn"]
            elif re.match(r'(if|else|for|while|return|import)\b', stripped):
                color = C["s_kw"]
            elif stripped.startswith('"') or stripped.startswith("'"):
                color = C["s_str"]
            bx = min(indent // 2, w - 4)
            ex = min(bx + max(4, len(stripped)//2), w - 1)
            self._minimap.create_rectangle(bx, y, ex, max(y+1, int(y+lh*0.8)),
                fill=color, outline="")

    def _minimap_click(self, e):
        h = self._minimap.winfo_height()
        frac = e.y / max(h, 1)
        self._editor.yview_moveto(frac)
        self._sync_gutter()

    # ─────────────────────────────────────────────────────────
    #  EDITOR EVENTS
    # ─────────────────────────────────────────────────────────
    def _on_key(self, e=None):
        tab = self._active_tab()
        if tab:
            src = self._editor.get("1.0", "end-1c")
            tab.modified = (hash(src) != tab.saved_hash)
            tab.content  = src
        self._rehighlight_current()
        self._sync_gutter()
        self._update_pos()
        self._schedule_minimap()
        if e and e.keysym not in (
            "Return","Tab","Escape","Up","Down","Left","Right",
            "BackSpace","Delete","space","Control_L","Control_R",
            "Alt_L","Alt_R","Shift_L","Shift_R"):
            self.after(300, self._maybe_autocomplete)

    def _on_click(self, e=None):
        self._update_pos()
        self._ac_popup.hide()

    def _on_up(self, e):
        if self._ac_popup.is_visible():
            self._ac_popup.navigate(-1)
            return "break"

    def _on_down(self, e):
        if self._ac_popup.is_visible():
            self._ac_popup.navigate(1)
            return "break"

    def _rehighlight_current(self):
        tab = self._active_tab()
        if not tab: return
        if tab.lang == "python":
            rehighlight(self._editor)
        else:
            src = self._editor.get("1.0", "end-1c")
            _regex_highlight_cpp(self._editor, src, tab.lang)

    def _auto_indent(self, event):
        idx    = self._editor.index("insert")
        line   = self._editor.get(f"{idx} linestart", idx)
        indent = len(line) - len(line.lstrip())
        if line.rstrip().endswith(":"):
            indent += 4
        self._editor.insert("insert", "\n" + " "*indent)
        return "break"

    def _insert_tab(self, event):
        try:
            self._editor.index("sel.first")
            self._indent_selection()
            return "break"
        except tk.TclError:
            pass
        self._editor.insert("insert", "    ")
        return "break"

    def _indent_selection(self):
        try:
            start = int(self._editor.index("sel.first").split(".")[0])
            end   = int(self._editor.index("sel.last").split(".")[0])
        except tk.TclError:
            return
        for ln in range(start, end+1):
            self._editor.insert(f"{ln}.0", "    ")

    def _unindent_selection(self, e=None):
        try:
            start = int(self._editor.index("sel.first").split(".")[0])
            end   = int(self._editor.index("sel.last").split(".")[0])
        except tk.TclError:
            ln = int(self._editor.index("insert").split(".")[0])
            start = end = ln
        for ln in range(start, end+1):
            text = self._editor.get(f"{ln}.0", f"{ln}.4")
            if text.startswith("    "):
                self._editor.delete(f"{ln}.0", f"{ln}.4")
            elif text.startswith("\t"):
                self._editor.delete(f"{ln}.0", f"{ln}.1")
        return "break"

    def _auto_close(self, event, closer):
        tab = self._active_tab()
        if not tab or tab.lang != "python": return
        self._editor.insert("insert", closer)
        self._editor.mark_set("insert",
            self._editor.index("insert - 1c"))

    def _match_brackets(self, e=None):
        self._editor.tag_remove("match_br", "1.0", "end")
        idx  = self._editor.index("insert")
        char = self._editor.get(idx)
        pairs = {"(":")", "[":"]", "{":"}",
                  ")":"(", "]":"[", "}":"{"}
        if char not in pairs: return
        close = pairs[char]
        forward = char in "([{"
        depth = 0
        pos   = idx
        while True:
            if forward:
                pos = self._editor.search(re.escape(char)+"|"+re.escape(close),
                    pos+"+1c", stopindex="end", regexp=True)
            else:
                pos = self._editor.search(re.escape(char)+"|"+re.escape(close),
                    pos+"-1c", stopindex="1.0", backwards=True, regexp=True)
            if not pos: break
            c = self._editor.get(pos)
            if c == char:  depth += 1
            else:
                if depth == 0:
                    self._editor.tag_add("match_br", idx, idx+"+1c")
                    self._editor.tag_add("match_br", pos, pos+"+1c")
                    break
                depth -= 1

    # ─────────────────────────────────────────────────────────
    #  AUTOCOMPLETE
    # ─────────────────────────────────────────────────────────
    def _trigger_autocomplete(self):
        src   = self._editor.get("1.0", "end-1c")
        idx   = self._editor.index("insert")
        ln, col = map(int, idx.split("."))
        items = self._completer.get_completions(src, ln, col)
        if not items: return
        try:
            bbox = self._editor.bbox(idx)
            if bbox:
                rx = self._editor.winfo_rootx() + bbox[0]
                ry = self._editor.winfo_rooty() + bbox[1] + bbox[3] + 2
            else:
                raise ValueError
        except Exception:
            rx = self.winfo_rootx() + 200
            ry = self.winfo_rooty() + 300

        def on_select(name):
            line = self._editor.get(f"{ln}.0", f"{ln}.{col}")
            m = re.search(r'[\w\.]+$', line)
            if m:
                start_col = col - len(m.group(0))
                self._editor.delete(f"{ln}.{start_col}", f"{ln}.{col}")
            self._editor.insert("insert", name)
            self._on_key()

        self._ac_popup.show(rx, ry, items, on_select)

    def _maybe_autocomplete(self):
        idx  = self._editor.index("insert")
        ln, col = map(int, idx.split("."))
        line = self._editor.get(f"{ln}.0", f"{ln}.{col}")
        m = re.search(r'\w{2,}$', line)
        if m and not self._ac_popup.is_visible():
            self._trigger_autocomplete()

    # ─────────────────────────────────────────────────────────
    #  EDITING COMMANDS
    # ─────────────────────────────────────────────────────────
    def _toggle_comment(self):
        tab = self._active_tab()
        if not tab: return
        cmt = "#" if tab.lang == "python" else "//"
        try:
            start = int(self._editor.index("sel.first").split(".")[0])
            end   = int(self._editor.index("sel.last").split(".")[0])
        except tk.TclError:
            start = end = int(self._editor.index("insert").split(".")[0])
        for ln in range(start, end+1):
            text = self._editor.get(f"{ln}.0", f"{ln}.end")
            stripped = text.lstrip()
            ws = len(text) - len(stripped)
            if stripped.startswith(cmt + " "):
                self._editor.delete(f"{ln}.{ws}", f"{ln}.{ws+len(cmt)+1}")
            elif stripped.startswith(cmt):
                self._editor.delete(f"{ln}.{ws}", f"{ln}.{ws+len(cmt)}")
            else:
                self._editor.insert(f"{ln}.{ws}", cmt + " ")

    def _duplicate_line(self):
        ln  = int(self._editor.index("insert").split(".")[0])
        text = self._editor.get(f"{ln}.0", f"{ln}.end")
        self._editor.insert(f"{ln}.end", "\n" + text)

    def _move_line_up(self):
        ln = int(self._editor.index("insert").split(".")[0])
        if ln <= 1: return
        text_cur  = self._editor.get(f"{ln}.0", f"{ln}.end")
        text_prev = self._editor.get(f"{ln-1}.0", f"{ln-1}.end")
        self._editor.delete(f"{ln-1}.0", f"{ln}.end")
        self._editor.insert(f"{ln-1}.0", text_cur + "\n" + text_prev)
        self._editor.mark_set("insert", f"{ln-1}.0")
        # FIX: Shift breakpoints so they follow the moved line
        tab = self._active_tab()
        if tab:
            new_bps = set()
            for bp in tab.bps:
                if bp == ln:       new_bps.add(ln - 1)
                elif bp == ln - 1: new_bps.add(ln)
                else:              new_bps.add(bp)
            tab.bps = new_bps
            self._editor.tag_remove("bp_ln", "1.0", "end")
            for bp in tab.bps:
                self._editor.tag_add("bp_ln", f"{bp}.0", f"{bp+1}.0")

    def _move_line_down(self):
        ln    = int(self._editor.index("insert").split(".")[0])
        total = int(self._editor.index("end").split(".")[0]) - 1
        if ln >= total: return
        text_cur  = self._editor.get(f"{ln}.0", f"{ln}.end")
        text_next = self._editor.get(f"{ln+1}.0", f"{ln+1}.end")
        self._editor.delete(f"{ln}.0", f"{ln+1}.end")
        self._editor.insert(f"{ln}.0", text_next + "\n" + text_cur)
        self._editor.mark_set("insert", f"{ln+1}.0")
        # FIX: Shift breakpoints so they follow the moved line
        tab = self._active_tab()
        if tab:
            new_bps = set()
            for bp in tab.bps:
                if bp == ln:       new_bps.add(ln + 1)
                elif bp == ln + 1: new_bps.add(ln)
                else:              new_bps.add(bp)
            tab.bps = new_bps
            self._editor.tag_remove("bp_ln", "1.0", "end")
            for bp in tab.bps:
                self._editor.tag_add("bp_ln", f"{bp}.0", f"{bp+1}.0")

    # ─────────────────────────────────────────────────────────
    #  DIALOGS
    # ─────────────────────────────────────────────────────────
    def _find_dialog(self):
        if self._find_win and self._find_win.winfo_exists():
            self._find_win.lift(); return
        win = tk.Toplevel(self)
        win.title("Find")
        win.geometry("440x96")
        win.configure(bg=C["bg_panel"])
        win.resizable(False, False)
        self._find_win = win
        row = tk.Frame(win, bg=C["bg_panel"])
        row.pack(fill="x", padx=10, pady=12)
        tk.Label(row, text="Find:", bg=C["bg_panel"], fg=C["fg"], font=UI, width=8, anchor="w").pack(side="left")
        fe = tk.Entry(row, bg=C["bg"], fg=C["fg"], insertbackground=C["fg"],
            font=MONO_S, relief="solid", bd=1,
            highlightthickness=1, highlightbackground=C["accent"])
        fe.pack(side="left", fill="x", expand=True, padx=6, ipady=4)
        fe.focus_set()
        def do_find(ev=None):
            self._editor.tag_remove("found","1.0","end")
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
        tk.Button(row, text="Find All", command=do_find,
            bg=C["accent"], fg=C["fg_white"], font=UI, relief="flat",
            bd=0, padx=12, pady=4, cursor="hand2").pack(side="left")

    def _find_replace_dialog(self):
        win = tk.Toplevel(self)
        win.title("Find & Replace")
        win.geometry("480x160")
        win.configure(bg=C["bg_panel"])
        win.resizable(False, False)
        win.grab_set()

        def row_lbl(text):
            r = tk.Frame(win, bg=C["bg_panel"])
            r.pack(fill="x", padx=12, pady=3)
            tk.Label(r, text=text, bg=C["bg_panel"], fg=C["fg"],
                font=UI, width=10, anchor="w").pack(side="left")
            e = tk.Entry(r, bg=C["bg"], fg=C["fg"], insertbackground=C["fg"],
                font=MONO_S, relief="solid", bd=1)
            e.pack(side="left", fill="x", expand=True, ipady=4)
            return e
        fe = row_lbl("Find:")
        re_e = row_lbl("Replace:")
        fe.focus_set()

        opt_row = tk.Frame(win, bg=C["bg_panel"])
        opt_row.pack(fill="x", padx=12)
        case_var = tk.BooleanVar()
        regex_var = tk.BooleanVar()
        tk.Checkbutton(opt_row, text="Case sensitive", variable=case_var,
            bg=C["bg_panel"], fg=C["fg"], selectcolor=C["bg_toolbar"],
            activebackground=C["bg_panel"], font=UI_S).pack(side="left")
        tk.Checkbutton(opt_row, text="Regex", variable=regex_var,
            bg=C["bg_panel"], fg=C["fg"], selectcolor=C["bg_toolbar"],
            activebackground=C["bg_panel"], font=UI_S).pack(side="left", padx=10)

        btn_row = tk.Frame(win, bg=C["bg_panel"])
        btn_row.pack(pady=8)
        def do_replace_all():
            q = fe.get(); r = re_e.get()
            if not q: return
            src = self._editor.get("1.0","end-1c")
            flags = 0 if case_var.get() else re.IGNORECASE
            try:
                if regex_var.get():
                    new_src = re.sub(q, r, src, flags=flags)
                else:
                    if not case_var.get():
                        new_src = re.sub(re.escape(q), r, src, flags=flags)
                    else:
                        new_src = src.replace(q, r)
                self._editor.delete("1.0","end")
                self._editor.insert("1.0", new_src)
                self._on_key()
            except re.error as ex:
                messagebox.showerror("Regex Error", str(ex), parent=win)
        for text, cmd in [("Replace All", do_replace_all), ("Close", win.destroy)]:
            tk.Button(btn_row, text=text, command=cmd,
                bg=C["accent"] if "Replace" in text else C["bg_toolbar"],
                fg=C["fg_white"] if "Replace" in text else C["fg"],
                font=UI, relief="flat", bd=0, padx=14, pady=5,
                cursor="hand2").pack(side="left", padx=4)

    def _goto_line_dialog(self):
        win = tk.Toplevel(self)
        win.title("Go to Line")
        win.geometry("300x100")
        win.configure(bg=C["bg_panel"])
        win.resizable(False, False)
        win.grab_set()
        total = int(self._editor.index("end").split(".")[0]) - 1
        tk.Label(win, text=f"Line (1 – {total}):",
            bg=C["bg_panel"], fg=C["fg"], font=UI).pack(pady=(14,4))
        e = tk.Entry(win, bg=C["bg"], fg=C["fg"], insertbackground=C["fg"],
            font=MONO_S, relief="solid", bd=1, justify="center")
        e.pack(padx=20, ipady=5)
        e.focus_set()
        def go(ev=None):
            try:
                ln = int(e.get())
                ln = max(1, min(ln, total))
                self._editor.see(f"{ln}.0")
                self._editor.mark_set("insert", f"{ln}.0")
                self._editor.focus_set()
                win.destroy()
            except ValueError:
                pass
        e.bind("<Return>", go)
        tk.Button(win, text="Go", command=go,
            bg=C["accent"], fg=C["fg_white"], font=UI_B,
            relief="flat", bd=0, padx=20, pady=5).pack(pady=6)

    def _command_palette(self):
        COMMANDS = [
            ("▶  Run / Debug (F5)",             self._run_or_continue),
            ("■  Stop Debugging (Shift+F5)",     self._stop),
            ("⤼  Step Over (F10)",               self._over),
            ("⤵  Step Into (F11)",               self._into),
            ("⤴  Step Out (Shift+F11)",          self._out),
            ("🆕  New Python File",               self._new),
            ("🆕  New C++ File",                  self._new_cpp),
            ("🆕  New GLSL File",                 self._new_glsl),
            ("📂  Open File…",                    self._open),
            ("💾  Save (Ctrl+S)",                 self._save),
            ("💾  Save As…",                      self._save_as),
            ("✕  Close Tab (Ctrl+W)",            self._close_tab),
            ("🔍  Find… (Ctrl+F)",               self._find_dialog),
            ("⇄  Find & Replace (Ctrl+H)",       self._find_replace_dialog),
            ("⌖  Go to Line (Ctrl+G)",           self._goto_line_dialog),
            ("💬  Toggle Comment (Ctrl+/)",       self._toggle_comment),
            ("©  Duplicate Line (Ctrl+D)",        self._duplicate_line),
            ("↑  Move Line Up (Alt+Up)",          self._move_line_up),
            ("↓  Move Line Down (Alt+Down)",      self._move_line_down),
            ("🔴  Toggle Breakpoint (F9)",        self._toggle_bp_cursor),
            ("🗑  Clear All Breakpoints",          self._clear_all_bps),
            ("+  Add Watch Expression",           self._add_watch_dialog),
            ("↻  Refresh Explorer",              self._refresh_explorer),
            ("🎨  Theme: Dark (VS2026)",          lambda: self._apply_theme("Dark (VS2026)")),
            ("🎨  Theme: Light (Classic)",        lambda: self._apply_theme("Light (Classic)")),
            ("🎨  Theme: High Contrast",          lambda: self._apply_theme("High Contrast")),
            ("ℹ  About Topdebug",                self._about_dialog),
            ("⌨  Keyboard Shortcuts",            self._shortcuts_dialog),
        ]
        win = tk.Toplevel(self)
        win.title("")
        win.geometry("560x360")
        win.configure(bg=C["bg_panel"])
        win.resizable(False, False)
        win.grab_set()
        tk.Frame(win, bg=C["accent"], height=3).pack(fill="x")
        tk.Label(win, text="Command Palette  (type to filter)",
            bg=C["bg_panel"], fg=C["fg_dim"], font=UI_S).pack(fill="x", padx=10, pady=(6,2))
        e = tk.Entry(win, bg=C["bg"], fg=C["fg"], insertbackground=C["fg"],
            font=MONO, relief="flat", bd=0,
            highlightthickness=1, highlightbackground=C["accent"])
        e.pack(fill="x", padx=10, ipady=6, pady=2)
        e.focus_set()
        lb = tk.Listbox(win, bg=C["bg_panel"], fg=C["fg"],
            selectbackground=C["accent"], selectforeground="#fff",
            font=UI, borderwidth=0, highlightthickness=0,
            activestyle="none", height=16)
        lb.pack(fill="both", expand=True, padx=10, pady=(2,6))

        def populate(q=""):
            lb.delete(0,"end")
            for name, _ in COMMANDS:
                if q.lower() in name.lower():
                    lb.insert("end", "  " + name)
            if lb.size() > 0:
                lb.selection_set(0); lb.activate(0)

        def on_select(ev=None):
            sel = lb.curselection()
            if not sel: return
            text = lb.get(sel[0]).strip()
            for name, cmd in COMMANDS:
                if name == text:
                    win.destroy()
                    cmd()
                    return

        def nav(direction):
            sel = lb.curselection()
            cur = sel[0] if sel else -1
            nxt = max(0, min(lb.size()-1, cur+direction))
            lb.selection_clear(0,"end")
            lb.selection_set(nxt); lb.activate(nxt); lb.see(nxt)

        e.bind("<KeyRelease>", lambda ev: populate(e.get()))
        e.bind("<Return>", on_select)
        e.bind("<Up>",   lambda ev: nav(-1))
        e.bind("<Down>", lambda ev: nav(1))
        lb.bind("<Double-Button-1>", on_select)
        lb.bind("<Return>", on_select)
        win.bind("<Escape>", lambda e: win.destroy())
        populate()

    def _shortcuts_dialog(self):
        win = tk.Toplevel(self)
        win.title("Keyboard Shortcuts")
        win.geometry("500x480")
        win.configure(bg=C["bg_panel"])

        tk.Frame(win, bg=C["accent"], height=3).pack(fill="x")
        tk.Label(win, text="  Keyboard Shortcuts",
            bg=C["bg_panel"], fg=C["fg_white"],
            font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=12, pady=8)

        txt = tk.Text(win, bg=C["bg"], fg=C["fg"],
            font=MONO_S, borderwidth=0, relief="flat",
            state="normal", wrap="none", padx=10, pady=8)
        txt.pack(fill="both", expand=True, padx=10, pady=(0,10))
        shortcuts = [
            ("DEBUGGING", ""),
            ("F5",              "Run / Continue"),
            ("Shift+F5",        "Stop Debugging"),
            ("F9",              "Toggle Breakpoint"),
            ("F10",             "Step Over"),
            ("F11",             "Step Into"),
            ("Shift+F11",       "Step Out"),
            ("", ""),
            ("FILE", ""),
            ("Ctrl+N",          "New Python File"),
            ("Ctrl+O",          "Open File"),
            ("Ctrl+S",          "Save"),
            ("Ctrl+Shift+S",    "Save As"),
            ("Ctrl+W",          "Close Tab"),
            ("", ""),
            ("EDITING", ""),
            ("Ctrl+Z/Y",        "Undo / Redo"),
            ("Ctrl+D",          "Duplicate Line"),
            ("Ctrl+/",          "Toggle Comment"),
            ("Alt+Up/Down",     "Move Line Up / Down"),
            ("Tab",             "Indent (selection)"),
            ("Shift+Tab",       "Unindent"),
            ("Ctrl+Space",      "Trigger Autocomplete"),
            ("", ""),
            ("NAVIGATION", ""),
            ("Ctrl+F",          "Find"),
            ("Ctrl+H",          "Find & Replace"),
            ("Ctrl+G",          "Go to Line"),
            ("Ctrl+Shift+P",    "Command Palette"),
        ]
        for key, desc in shortcuts:
            if not key and not desc:
                txt.insert("end", "\n")
            elif not desc:
                txt.insert("end", f"\n  ── {key} ──\n", "cat")
            else:
                txt.insert("end", f"  {key:<22} {desc}\n")
        txt.tag_config("cat", foreground=C["accent2"],
            font=(*MONO_S[:1], MONO_S[1], "bold"))
        txt.config(state="disabled")

    def _about_dialog(self):
        win = tk.Toplevel(self)
        win.title("About Topdebug")
        win.geometry("460x280")
        win.configure(bg=C["bg_panel"])
        win.resizable(False, False)
        win.grab_set()

        hdr = tk.Frame(win, bg=C["bg"], height=72)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Frame(hdr, bg=C["accent"], height=3).pack(fill="x", side="top")
        inner = tk.Frame(hdr, bg=C["bg"])
        inner.pack(fill="both", expand=True, padx=16)
        tk.Label(inner, text="Topdebug", bg=C["bg"], fg=C["fg_white"],
            font=("Segoe UI", 20, "bold")).pack(side="left", pady=10)
        tk.Label(inner, text=" v2.0", bg=C["bg"], fg=C["fg_dim"],
            font=("Segoe UI", 11)).pack(side="left", pady=10)

        body = tk.Frame(win, bg=C["bg_panel"])
        body.pack(fill="both", expand=True, padx=16, pady=10)
        for line in [
            "Advanced Python / C++ / GLSL IDE",
            "Pure Python · stdlib only · tkinter UI",
            "",
            "✔  Multi-tab editor",
            "✔  Full Python debugger (breakpoints, step, watch)",
            "✔  C++ compile & run via g++",
            "✔  IntelliSense autocomplete",
            "✔  Symbol outline · Minimap · Breadcrumbs",
            "✔  Find & Replace · Command Palette",
            "✔  3 built-in themes",
        ]:
            tk.Label(body, text=line, bg=C["bg_panel"],
                fg=C["fg"] if line.startswith("✔") else C["fg_dim"],
                font=UI if line.startswith("✔") else UI_S,
                anchor="w").pack(fill="x")
        tk.Button(win, text="  Close  ", command=win.destroy,
            bg=C["accent"], fg=C["fg_white"], font=UI_B,
            relief="flat", bd=0, padx=14, pady=5,
            cursor="hand2").pack(pady=(0,12))

    # ─────────────────────────────────────────────────────────
    #  WATCH PANEL
    # ─────────────────────────────────────────────────────────
    def _build_watch_panel(self, parent):
        ctrl = tk.Frame(parent, bg=C["bg_panel"])
        ctrl.pack(fill="x", pady=2)
        tk.Button(ctrl, text="+ Add", command=self._add_watch_dialog,
            bg=C["bg_toolbar"], fg=C["fg"], font=UI_S,
            relief="flat", bd=0, padx=8, pady=2,
            cursor="hand2").pack(side="left", padx=2)
        tk.Button(ctrl, text="✕ Remove", command=self._remove_watch,
            bg=C["bg_toolbar"], fg=C["fg"], font=UI_S,
            relief="flat", bd=0, padx=8, pady=2,
            cursor="hand2").pack(side="left")
        self._watch_tree = self._make_tree(parent, ("Expression","Value"))

    def _add_watch_dialog(self):
        win = tk.Toplevel(self)
        win.title("Add Watch")
        win.geometry("380x120")
        win.configure(bg=C["bg_panel"])
        win.resizable(False, False)
        win.grab_set()
        tk.Label(win, text="Watch Expression:", bg=C["bg_panel"],
            fg=C["fg"], font=UI_B).pack(anchor="w", padx=14, pady=(14,4))
        e = tk.Entry(win, bg=C["bg"], fg=C["fg"], insertbackground=C["fg"],
            font=MONO_S, relief="solid", bd=1,
            highlightthickness=1, highlightbackground=C["accent"])
        e.pack(fill="x", padx=14, ipady=5)
        e.focus_set()
        def ok(ev=None):
            expr = e.get().strip()
            if expr:
                self._watches.append(expr)
                self._refresh_watches()
            win.destroy()
        e.bind("<Return>", ok)
        btns = tk.Frame(win, bg=C["bg_panel"])
        btns.pack(pady=10)
        for text, cmd, ac in [("  OK  ", ok, True), ("Cancel", win.destroy, False)]:
            tk.Button(btns, text=text, command=cmd,
                bg=C["accent"] if ac else C["bg_toolbar"],
                fg=C["fg_white"] if ac else C["fg"],
                font=UI_B if ac else UI,
                relief="flat", bd=0, padx=10, pady=4,
                cursor="hand2").pack(side="left", padx=4)

    def _remove_watch(self):
        sel = self._watch_tree.selection()
        if sel:
            idx = self._watch_tree.index(sel[0])
            if 0 <= idx < len(self._watches):
                self._watches.pop(idx)
                self._refresh_watches()

    def _refresh_watches(self):
        for row in self._watch_tree.get_children():
            self._watch_tree.delete(row)
        for expr in self._watches:
            try:
                val = repr(eval(expr, {}, self._dbg_locals))
                if len(val) > 60: val = val[:57]+"…"
            except Exception as ex:
                val = f"<{type(ex).__name__}: {ex}>"
            self._watch_tree.insert("","end", values=(expr, val))

    # ─────────────────────────────────────────────────────────
    #  FILE EXPLORER
    # ─────────────────────────────────────────────────────────
    def _refresh_explorer(self):
        self._explorer.delete(*self._explorer.get_children())
        cwd = os.getcwd()
        root_node = self._explorer.insert("","end",
            text=f"📁 {os.path.basename(cwd)}", open=True)
        CODE_EXTS = {'.py','.cpp','.cxx','.cc','.c','.h','.hpp',
                     '.glsl','.vert','.frag','.geom','.comp'}
        icon_map  = {'.py':'🐍','.cpp':'⚙','.c':'⚙','.h':'📋',
                     '.hpp':'📋','.glsl':'🎨','.vert':'🎨',
                     '.frag':'🎨','.geom':'🎨','.comp':'🎨'}
        try:
            for name in sorted(os.listdir(cwd)):
                ext  = os.path.splitext(name)[1].lower()
                full = os.path.join(cwd, name)
                if ext in CODE_EXTS or os.path.isdir(full):
                    icon = "📁" if os.path.isdir(full) else icon_map.get(ext,"📄")
                    self._explorer.insert(root_node,"end",
                        text=f"{icon} {name}",
                        values=[full])
        except Exception:
            pass

    def _explorer_open(self, e):
        sel = self._explorer.selection()
        if sel:
            vals = self._explorer.item(sel[0],"values")
            if vals:
                path = vals[0]
                CODE_EXTS = {'.py','.cpp','.cxx','.cc','.c','.h','.hpp',
                             '.glsl','.vert','.frag','.geom','.comp'}
                if os.path.isfile(path) and os.path.splitext(path)[1].lower() in CODE_EXTS:
                    self._load_file(path)

    # ─────────────────────────────────────────────────────────
    #  FILE OPERATIONS
    # ─────────────────────────────────────────────────────────
    def _apply_language_setup_for(self, tab):
        if tab.lang == "python":
            setup_tags(self._editor)
            rehighlight(self._editor)
            badge = " 🐍 Python "
            badge_color = "#3572A5"
            btn_text = "▶  Run / Debug (F5)"
        elif tab.lang == "cpp":
            setup_tags_cpp(self._editor)
            src = self._editor.get("1.0","end-1c")
            _regex_highlight_cpp(self._editor, src, "cpp")
            badge = " ⚙ C++ "
            badge_color = "#f34b7d"
            btn_text = "▶  Compile & Run"
        else:
            setup_tags_cpp(self._editor)
            src = self._editor.get("1.0","end-1c")
            _regex_highlight_cpp(self._editor, src, "glsl")
            badge = " 🎨 GLSL "
            badge_color = "#7c4dff"
            btn_text = "▷  Syntax Only"
        try:
            self._langseg.config(text=f"  {badge}  ")
            self._btn_run.config(text=btn_text)
        except Exception:
            pass

    def _new(self):
        tab = EditorTab(content=DEFAULT_CODE, lang="python")
        self._tabs.append(tab)
        self._render_tabs()
        self._switch_tab(len(self._tabs)-1)

    def _new_cpp(self):
        tab = EditorTab(content=DEFAULT_CPP_CODE, lang="cpp")
        tab.path = None
        self._tabs.append(tab)
        self._render_tabs()
        self._switch_tab(len(self._tabs)-1)

    def _new_glsl(self):
        tab = EditorTab(content=DEFAULT_GLSL_CODE, lang="glsl")
        self._tabs.append(tab)
        self._render_tabs()
        self._switch_tab(len(self._tabs)-1)

    def _open(self):
        p = filedialog.askopenfilename(
            filetypes=[
                ("All supported","*.py *.cpp *.cxx *.cc *.c *.h *.hpp *.glsl *.vert *.frag *.geom *.comp"),
                ("Python","*.py"),
                ("C/C++","*.cpp *.cxx *.cc *.c *.h *.hpp"),
                ("GLSL Shader","*.glsl *.vert *.frag *.geom *.comp *.tesc *.tese"),
                ("All","*.*"),
            ])
        if p: self._load_file(p)

    def _load_file(self, path):
        for i, tab in enumerate(self._tabs):
            if tab.path and os.path.abspath(tab.path) == os.path.abspath(path):
                self._switch_tab(i)
                return
        try:
            with open(path, "r", encoding="utf-8") as f:
                src = f.read()
        except Exception as ex:
            messagebox.showerror("Error", f"Cannot open file:\n{ex}")
            return
        lang = detect_language(path)
        tab  = EditorTab(path=path, content=src, lang=lang)
        tab.saved_hash = hash(src)
        self._tabs.append(tab)
        self._render_tabs()
        self._switch_tab(len(self._tabs)-1)
        abs_path = os.path.abspath(path)
        if abs_path in self._recent_files:
            self._recent_files.remove(abs_path)
        self._recent_files.insert(0, abs_path)
        self._recent_files = self._recent_files[:20]
        self._settings["recent_files"] = self._recent_files
        save_settings(self._settings)
        self._rebuild_recent_menu()

    def _save(self):
        tab = self._active_tab()
        if not tab: return
        if tab.path:
            try:
                src = self._editor.get("1.0","end-1c")
                with open(tab.path,"w",encoding="utf-8") as f:
                    f.write(src)
                tab.content    = src
                tab.saved_hash = hash(src)
                tab.modified   = False
                self._render_tabs()
                self.log(f"Saved: {tab.path}\n","info")
            except Exception as ex:
                messagebox.showerror("Save Error", str(ex))
        else:
            self._save_as()

    def _save_as(self):
        tab = self._active_tab()
        if not tab: return
        ext_map = {"python":".py","cpp":".cpp","glsl":".frag"}
        p = filedialog.asksaveasfilename(
            defaultextension=ext_map.get(tab.lang,".py"),
            filetypes=[
                ("Python","*.py"),("C/C++","*.cpp *.c *.h *.hpp"),
                ("GLSL Shader","*.glsl *.vert *.frag *.geom *.comp"),("All","*.*")])
        if p:
            tab.path = p
            tab.lang = detect_language(p)
            self._save()
            self._apply_language_setup_for(tab)
            self._render_tabs()
            self._update_filelbl(tab)
            self._refresh_explorer()

    # ─────────────────────────────────────────────────────────
    #  DEBUG ACTIONS
    # ─────────────────────────────────────────────────────────
    def _set_dbg_btns(self, active):
        state = "normal" if active else "disabled"
        for b in (self._btn_stop, self._btn_over, self._btn_into, self._btn_out):
            b.config(state=state)

    def _run_or_continue(self):
        tab = self._active_tab()
        if not tab: return
        if tab.lang in ("cpp","glsl"):
            self._run_cpp(); return
        if self._running:
            if self._dbg: self._dbg.cmd_continue()
            return
        src = self._editor.get("1.0","end-1c").strip()
        if not src: return

        tab.content = src

        # FIX: Flush editor bp tags into tab.bps BEFORE starting the debugger.
        tab.bps = self._bps_for_active()

        self._clear_output()

        # FIX: Use tab.debug_filename as the single source of truth for the
        # filename passed to both compile() and set_break().
        debug_fname = tab.debug_filename

        self._dbg = Debugger(self)

        # THE REAL FIX: bdb.set_break() validates line numbers by looking up
        # the file in linecache. For unsaved in-memory code, linecache has
        # nothing, so set_break silently fails and registers NO breakpoint.
        # Solution: manually inject the source into linecache BEFORE set_break.
        import linecache
        src_lines = src.splitlines(True)
        if not src_lines[-1].endswith('\n'):
            src_lines[-1] += '\n'
        linecache.cache[debug_fname] = (len(src), None, src_lines, debug_fname)

        if tab.bps:
            for ln in sorted(tab.bps):
                err = self._dbg.set_break(debug_fname, ln)
                if err:
                    self.log(f"[BP warning line {ln}]: {err}\n", "warn")
                else:
                    self.log(f"[Breakpoint set at line {ln}]\n", "info")
            # Don't set_step() when we have breakpoints — just run to them.
        else:
            # No breakpoints: step through every line so user sees execution.
            self._dbg.set_step()

        self._running    = True
        self._dbg_locals = {}
        self._set_dbg_btns(True)
        self._btn_run.config(state="normal", text="▶▶ Continue (F5)")
        self._status(f"  ▶  Debugging: {tab.name}", C["bg_statusbar_dbg"])
        # FIX: Lock editor during debug so code can't be changed mid-session
        self._lock_editor()

        def runner():
            old_o, old_e = sys.stdout, sys.stderr
            sys.stdout = Redirect(lambda t, tag=None: self.after(0, self.log, t, tag))
            sys.stderr = Redirect(lambda t, tag=None: self.after(0, self.log, t, "err"))
            try:    self._dbg.execute(src, debug_fname)
            finally:
                sys.stdout = old_o
                sys.stderr = old_e
        threading.Thread(target=runner, daemon=True).start()

    def _run_cpp(self):
        tab = self._active_tab()
        if not tab: return
        if tab.lang == "glsl":
            self.log("[GLSL] Syntax highlight only — cannot run standalone.\n","info")
            return
        src = self._editor.get("1.0","end-1c").strip()
        if not src: return
        self._clear_output()

        if tab.path and tab.path.endswith(('.cpp','.cxx','.cc','.c')):
            src_path = tab.path
            with open(src_path,"w",encoding="utf-8") as f: f.write(src)
        else:
            tmp = tempfile.NamedTemporaryFile(suffix=".cpp",delete=False,mode="w",encoding="utf-8")
            tmp.write(src); tmp.close()
            src_path = tmp.name

        out_path = re.sub(r'\.(cpp|cxx|cc|c)$','',src_path) + "_out"
        if sys.platform=="win32": out_path += ".exe"

        self._status(f"  ⚙  Compiling {os.path.basename(src_path)} …", C["orange"])
        self.log(f"[Compile]  g++ {os.path.basename(src_path)} → {os.path.basename(out_path)}\n","info")

        def compile_and_run():
            result = subprocess.run(
                ["g++","-std=c++17","-O2",src_path,"-o",out_path,
                 "-lGL","-lGLEW","-lglfw"],
                capture_output=True, text=True)
            if result.stdout: self.after(0,self.log,result.stdout)
            if result.stderr:
                tag = "err" if result.returncode != 0 else "info"
                self.after(0,self.log,result.stderr,tag)
                for ln_txt in result.stderr.splitlines():
                    m = re.match(r'(.+?):(\d+):(\d+):\s*(error|warning):\s*(.+)', ln_txt)
                    if m:
                        kind = "E" if m.group(4)=="error" else "W"
                        self.after(0,self._add_error,
                            m.group(4).upper(), m.group(5),
                            os.path.basename(m.group(1)),
                            m.group(2), m.group(3), kind)
            if result.returncode != 0:
                self.after(0,self.log,"\n[Compilation FAILED]\n","err")
                self.after(0,self._status,"  ✕  Compilation failed",C["red"]); return

            self.after(0,self.log,"[OK]  Running…\n\n","ok")
            self.after(0,self._status,f"  ▶  Running: {os.path.basename(out_path)}",C["green"])
            try:
                proc = subprocess.Popen([out_path],stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,text=True)
                for line in proc.stdout:
                    self.after(0,self.log,line)
                proc.wait()
                tag = "ok" if proc.returncode==0 else "err"
                self.after(0,self.log,f"\n[Process exited with code {proc.returncode}]\n",tag)
                self.after(0,self._status,
                    f"  ✓  Finished ({proc.returncode})" if proc.returncode==0
                    else f"  ✕  Exited ({proc.returncode})",
                    C["green"] if proc.returncode==0 else C["red"])
            except FileNotFoundError:
                self.after(0,self.log,"\n[Cannot run — check permissions or g++ path]\n","err")
            except Exception as ex:
                self.after(0,self.log,f"\n[Run error: {ex}]\n","err")
        threading.Thread(target=compile_and_run, daemon=True).start()

    def _stop(self):
        if self._dbg: self._dbg.cmd_stop()
        self._running    = False
        self._dbg_line   = None
        self._dbg_locals = {}
        self._set_dbg_btns(False)
        self._btn_run.config(text="▶  Run / Debug (F5)")
        self._editor.tag_remove("curdbg","1.0","end")
        # FIX: Unlock editor when debug stops
        self._unlock_editor()
        self._sync_gutter()
        self._status("  ■  Stopped", C["bg_statusbar"])

    def _over(self):
        if self._running and self._dbg: self._dbg.cmd_next()
    def _into(self):
        if self._running and self._dbg: self._dbg.cmd_step()
    def _out(self):
        if self._running and self._dbg: self._dbg.cmd_return()

    # ─────────────────────────────────────────────────────────
    #  DEBUGGER CALLBACKS
    # ─────────────────────────────────────────────────────────
    def dbg_paused(self, fname, lineno, locals_, stack):
        self._dbg_line   = lineno
        self._dbg_locals = locals_
        self._editor.tag_remove("curdbg","1.0","end")
        self._editor.tag_add("curdbg",f"{lineno}.0",f"{lineno+1}.0")
        self._editor.see(f"{lineno}.0")
        self._sync_gutter()
        self._fill_vars(locals_)
        self._fill_stack(stack)
        self._refresh_watches()
        self._status(f"  ⏸  Paused — Line {lineno}", C["bg_statusbar_dbg"])

    def dbg_done(self):
        self._running    = False
        self._dbg_line   = None
        self._dbg_locals = {}
        self._set_dbg_btns(False)
        self._btn_run.config(text="▶  Run / Debug (F5)")
        self._editor.tag_remove("curdbg","1.0","end")
        # FIX: Unlock editor when debug finishes
        self._unlock_editor()
        self._sync_gutter()
        self._fill_vars({})
        self._fill_stack([])
        self._refresh_watches()
        self._status("  ✓  Finished", C["bg_statusbar"])
        self.log("\n[Program finished]\n","ok")

    def _fill_vars(self, locs):
        for r in self._vars_tree.get_children(): self._vars_tree.delete(r)
        for k, v in sorted(locs.items()):
            if k.startswith("__"): continue
            try:
                t  = type(v).__name__
                rv = repr(v)
                if len(rv) > 80: rv = rv[:77]+"…"
            except Exception: t="?"; rv="?"
            self._vars_tree.insert("","end",values=(k,rv,t))

    def _fill_stack(self, stack):
        for r in self._stack_tree.get_children(): self._stack_tree.delete(r)
        for fn, ln, name in stack:
            self._stack_tree.insert("","end",
                values=(name, os.path.basename(fn), ln))

    # ─────────────────────────────────────────────────────────
    #  OUTPUT / CONSOLE
    # ─────────────────────────────────────────────────────────
    def log(self, text, tag=None):
        self._out.config(state="normal")
        if tag: self._out.insert("end", text, tag)
        else:   self._out.insert("end", text)
        self._out.see("end")
        self._out.config(state="disabled")

    def _add_error(self, code, desc, fname, line, col, kind="E"):
        icon = "⊘" if kind=="E" else "⚠"
        self._err_tree.insert("","end",
            values=(f"{icon} {code}", desc, fname, line, col),
            tags=(kind,))
        self._err_tree.tag_config("E", foreground=C["red"])
        self._err_tree.tag_config("W", foreground=C["orange"])
        items = self._err_tree.get_children()
        errs  = sum(1 for i in items if self._err_tree.item(i,"values")[0].startswith("⊘"))
        warns = sum(1 for i in items if self._err_tree.item(i,"values")[0].startswith("⚠"))
        try:
            self._err_count_lbl.config(
                text=f"⊘ {errs} Errors   ⚠ {warns} Warnings   ℹ 0 Messages")
        except Exception: pass

    def _clear_errors(self):
        for i in self._err_tree.get_children(): self._err_tree.delete(i)
        try: self._err_count_lbl.config(text="⊘ 0 Errors   ⚠ 0 Warnings   ℹ 0 Messages")
        except Exception: pass

    def _repl_exec(self, e=None):
        cmd = self._con_in.get().strip()
        if not cmd: return
        self._repl_hist.appendleft(cmd)
        self._repl_hidx = -1
        self._con_out_write(f">>> {cmd}\n","prompt")
        self._con_in.delete(0,"end")

        # FIX: Use Redirect class so runsource() output is actually captured.
        # The old fake W class didn't work because InteractiveInterpreter
        # writes to sys.stdout directly, which Redirect correctly intercepts.
        old_o, old_e = sys.stdout, sys.stderr
        sys.stdout = Redirect(lambda t, tag=None: self._con_out_write(t))
        sys.stderr = Redirect(lambda t, tag=None: self._con_out_write(t, "err"))
        try:
            self._repl_interp.runsource(cmd)
        except Exception:
            self._con_out_write(traceback.format_exc(), "err")
        finally:
            sys.stdout, sys.stderr = old_o, old_e

    def _repl_hist_up(self, e):
        hist = list(self._repl_hist)
        if hist:
            self._repl_hidx = min(len(hist)-1, self._repl_hidx+1)
            self._con_in.delete(0,"end")
            self._con_in.insert(0, hist[self._repl_hidx])
        return "break"

    def _repl_hist_down(self, e):
        if self._repl_hidx > 0:
            self._repl_hidx -= 1
            self._con_in.delete(0,"end")
            self._con_in.insert(0, list(self._repl_hist)[self._repl_hidx])
        else:
            self._repl_hidx = -1
            self._con_in.delete(0,"end")
        return "break"

    def _repl_clear(self):
        self._con_out.config(state="normal")
        self._con_out.delete("1.0","end")
        self._con_out.config(state="disabled")

    def _con_out_write(self, text, tag=None):
        self._con_out.config(state="normal")
        if tag: self._con_out.insert("end", text, tag)
        else:   self._con_out.insert("end", text)
        self._con_out.see("end")
        self._con_out.config(state="disabled")

    # ─────────────────────────────────────────────────────────
    #  HELPERS
    # ─────────────────────────────────────────────────────────
    def _make_tree(self, parent, cols):
        f = tk.Frame(parent, bg=C["bg_panel"])
        f.pack(fill="both", expand=True)
        tree = ttk.Treeview(f, columns=cols, show="headings",
            style="VS.Treeview", selectmode="browse")
        w = 80 if len(cols) == 3 else 130
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=w, stretch=True)
        vsb = tk.Scrollbar(f, orient="vertical", command=tree.yview,
            width=10, bg=C["bg_toolbar"])
        vsb.pack(side="right", fill="y")
        tree.config(yscrollcommand=vsb.set)
        tree.pack(fill="both", expand=True)
        return tree

    def _on_configure(self, e=None):
        self._sync_gutter()
        self._settings["geometry"] = self.geometry()
        save_settings(self._settings)

    def _on_close(self):
        # FIX: Cancel the clock timer to prevent TclError after destroy()
        if self._clock_job:
            self.after_cancel(self._clock_job)
            self._clock_job = None
        if self._minimap_job:
            self.after_cancel(self._minimap_job)
            self._minimap_job = None

        # FIX: Stop any running debug session cleanly
        if self._running and self._dbg:
            self._dbg.cmd_stop()

        # Make sure active tab content is up to date
        if self._active_tab_idx >= 0 and self._active_tab_idx < len(self._tabs):
            self._tabs[self._active_tab_idx].content = self._editor.get("1.0","end-1c")

        for tab in self._tabs:
            src = tab.content
            if hash(src) != tab.saved_hash:
                ans = messagebox.askyesnocancel(
                    "Unsaved Changes",
                    f"Save '{tab.name}' before closing?")
                if ans is None: return   # user cancelled — abort close
                if ans:
                    if tab.path:
                        try:
                            with open(tab.path,"w",encoding="utf-8") as f:
                                f.write(src)
                        except Exception as ex:
                            messagebox.showerror("Save Error", str(ex))
                            return
                    else:
                        # FIX: Unsaved new file — open Save As dialog
                        ext_map = {"python":".py","cpp":".cpp","glsl":".frag"}
                        p = filedialog.asksaveasfilename(
                            title=f"Save '{tab.name}' before closing",
                            defaultextension=ext_map.get(tab.lang,".py"),
                            filetypes=[("Python","*.py"),("C/C++","*.cpp *.c"),
                                       ("GLSL","*.glsl *.frag"),("All","*.*")])
                        if p:
                            try:
                                with open(p,"w",encoding="utf-8") as f:
                                    f.write(src)
                            except Exception as ex:
                                messagebox.showerror("Save Error", str(ex))
                                return
                        # If user cancels Save As, we still close (they chose not to save)
        save_settings(self._settings)
        self.destroy()

# ═══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = IDE()
    app.mainloop()