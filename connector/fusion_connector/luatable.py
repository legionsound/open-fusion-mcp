"""Tolerant parser for Fusion .setting/.comp Lua-table text."""
import re

class LTable:
    __slots__ = ("ctor", "items", "args")
    def __init__(self, ctor=None, items=None, args=None):
        self.ctor = ctor; self.items = items or []; self.args = args
    def get(self, k, d=None):
        for kk, v in self.items:
            if kk == k: return v
        return d
    def keys(self): return [k for k, _ in self.items]
    def positional(self): return [v for k, v in self.items if isinstance(k, tuple) and k[0] == '#']
    def __repr__(self): return f"LTable({self.ctor},{len(self.items)})"

class Ctor:  # ctor without table, e.g. ordered() or Identifier(...)
    __slots__ = ("name", "args")
    def __init__(self, name, args): self.name = name; self.args = args
    def __repr__(self): return f"Ctor({self.name})"

TOK = re.compile(r"""
 (?P<ws>\s+)
|(?P<comment>--(?:\[(?P<ceq>=*)\[.*?\](?P=ceq)\]|[^\n]*))
|(?P<lstr>\[(?P<leq>=*)\[.*?\](?P=leq)\])
|(?P<str>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')
|(?P<num>-?(?:0[xX][0-9a-fA-F]+|(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?(?:\#(?:INF|IND|QNAN|SNAN)\d*)?))
|(?P<ident>[A-Za-z_][A-Za-z0-9_.]*)
|(?P<op>[{}()\[\]=,;\-+*/])
""", re.S | re.X)

def tokenize(s):
    pos = 0; out = []; n = len(s)
    while pos < n:
        m = TOK.match(s, pos)
        if not m:
            raise ValueError(f"bad char at {pos}: {s[pos:pos+30]!r}")
        pos = m.end(); k = m.lastgroup
        if k in ('ws', 'comment', 'ceq'): continue
        if m.group('ws') is not None or m.group('comment') is not None: continue
        if m.group('lstr') is not None:
            t = m.group('lstr'); eq = len(m.group('leq'))
            body = t[2+eq:-(2+eq)]
            if body.startswith('\n'): body = body[1:]
            out.append(('str', body)); continue
        if m.group('str') is not None:
            t = m.group('str')[1:-1]
            t = re.sub(r'\\(n|t|r|"|\'|\\|\d{1,3})', lambda mm: {'n':'\n','t':'\t','r':'\r','"':'"',"'":"'",'\\':'\\'}.get(mm.group(1), chr(int(mm.group(1))) if mm.group(1).isdigit() else mm.group(1)), t)
            out.append(('str', t)); continue
        if m.group('num') is not None:
            t = m.group('num')
            try:
                v = float(int(t, 16)) if t.lower().startswith(('0x','-0x')) else float(t.split('#')[0]) if '#' not in t else float('inf')
            except Exception:
                v = float('nan')
            out.append(('num', v)); continue
        if m.group('ident') is not None:
            out.append(('ident', m.group('ident'))); continue
        out.append(('op', m.group('op')))
    return out

class Parser:
    def __init__(self, toks): self.t = toks; self.i = 0
    def peek(self, o=0):
        j = self.i + o
        return self.t[j] if j < len(self.t) else ('eof', None)
    def next(self):
        tok = self.peek(); self.i += 1; return tok
    def expect(self, v):
        tok = self.next()
        if tok[1] != v: raise ValueError(f"expected {v} got {tok} at {self.i}")
    def value(self):
        k, v = self.peek()
        if k == 'str':
            self.i += 1
            # string concatenation a .. b is rare; ignore
            return v
        if k == 'num':
            self.i += 1; return v
        if k == 'op' and v == '{':
            return self.table(None)
        if k == 'op' and v == '-':
            self.i += 1; x = self.value()
            return -x if isinstance(x, float) else x
        if k == 'ident':
            self.i += 1
            if v == 'true': return True
            if v == 'false': return False
            if v == 'nil': return None
            args = None
            if self.peek() == ('op', '('):
                self.i += 1; args = []
                while self.peek() != ('op', ')'):
                    args.append(self.value())
                    if self.peek() == ('op', ','): self.i += 1
                self.i += 1
            if self.peek() == ('op', '{'):
                t = self.table(v); t.args = args; return t
            if self.peek()[0] == 'str':  # Ident "str" call sugar
                s = self.next()[1]; return LTable(v, [(('#',1), s)])
            return Ctor(v, args)
        raise ValueError(f"unexpected {k} {v} at tok {self.i}")
    def table(self, ctor):
        self.expect('{'); items = []; pos = 1
        while True:
            k, v = self.peek()
            if k == 'op' and v == '}': self.i += 1; break
            if k == 'op' and v in (',', ';'): self.i += 1; continue
            if k == 'op' and v == '[':
                self.i += 1; key = self.value(); self.expect(']'); self.expect('=')
                if isinstance(key, float) and key == int(key): key = key  # numeric key
                items.append((key, self.value())); continue
            if k == 'ident' and self.peek(1) == ('op', '='):
                self.i += 2; items.append((v, self.value())); continue
            items.append((('#', pos), self.value())); pos += 1
        return LTable(ctor, items)

def parse(text):
    toks = tokenize(text)
    p = Parser(toks)
    v = p.value()
    return v
