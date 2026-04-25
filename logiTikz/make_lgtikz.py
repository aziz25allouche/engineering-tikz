#!/usr/bin/env python3
"""
Generates .lgtikz files compatible with logiTikz.sty
Uses the same colors defined in the .sty (lgwire, lggf, lggb, lgnot, lgin...)
"""
import sys, re, argparse
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

@dataclass
class Node:
    kind: str
    label: str = ""
    children: List['Node'] = field(default_factory=list)
    def depth(self):
        return 0 if not self.children else 1+max(c.depth() for c in self.children)

class Lexer:
    def __init__(self, s):
        self.toks, self.i = [], 0
        pat = re.compile(
            r'(?P<LP>\()|(?P<RP>\))|(?P<NOT>[!~])|(?P<XOR>\^)'
            r'|(?P<AND>[.*&])|(?P<OR>[+|])|(?P<VAR>[A-Za-z][A-Za-z0-9_\']*)'
            r'|(?P<WS>\s+)')
        for m in pat.finditer(s):
            if m.lastgroup != 'WS':
                self.toks.append((m.lastgroup, m.group()))
    def peek(self): return self.toks[self.i] if self.i < len(self.toks) else None
    def consume(self, k=None):
        t = self.toks[self.i]
        if k and t[0] != k: raise SyntaxError(f"Attendu {k}, obtenu {t}")
        self.i += 1; return t
    def more(self): return self.i < len(self.toks)

class Parser:
    def __init__(self, e): self.l = Lexer(e)
    def parse(self):
        n = self.expr()
        if self.l.more(): raise SyntaxError(f"Token inattendu: {self.l.peek()}")
        return n
    def expr(self):
        n = self.term()
        while self.l.peek() and self.l.peek()[0] == 'OR':
            self.l.consume(); n = Node('or','+', [n, self.term()])
        return n
    def term(self):
        n = self.factor()
        while self.l.peek() and self.l.peek()[0] == 'AND':
            self.l.consume(); n = Node('and','.',[n, self.factor()])
        return n
    def factor(self):
        if self.l.peek() and self.l.peek()[0] == 'NOT':
            self.l.consume(); return Node('not','!',[self.factor()])
        return self.xor()
    def xor(self):
        n = self.atom()
        while self.l.peek() and self.l.peek()[0] == 'XOR':
            self.l.consume(); n = Node('xor','^',[n, self.atom()])
        return n
    def atom(self):
        t = self.l.peek()
        if not t: raise SyntaxError("Expression incomplète")
        if t[0] == 'LP':
            self.l.consume(); n = self.expr(); self.l.consume('RP'); return n
        if t[0] == 'VAR':
            self.l.consume(); return Node('var', t[1])
        raise SyntaxError(f"Symbole inattendu: {t}")

# Gate style names matching logiTikz.sty
GATE_TIKZ = {
    'and':'and gate US', 'or':'or gate US', 'not':'not gate US',
    'xor':'xor gate US', 'nand':'nand gate US', 'nor':'nor gate US',
}
GATE_STYLE = {
    'and':'lggate', 'or':'lggate', 'not':'lgnot',
    'xor':'lggate', 'nand':'lggate', 'nor':'lggate',
}

class TikZGen:
    X=1; Y=3.2
    def __init__(self, output='S'):
        self.output=output
        self._ctr=0; self._nodes=[]; self._wires=[]
        self._pos: Dict[int,Tuple[float,float]]={}
        self._varid: Dict[str,str]={}
        self._var_cols: Dict[str,float]={}
        self._col=0

    def _nid(self,p='G'):
        self._ctr+=1; return f"{p}{self._ctr}"

    def _layout(self, node, col):
        if node.kind=='var':
            lbl=node.label
            if lbl in self._var_cols:
                self._pos[id(node)]=(self._var_cols[lbl]*self.X, 0)
                return self._var_cols[lbl]
            c=self._col; self._col+=1
            self._pos[id(node)]=(c*self.X-2, 0)
            self._var_cols[lbl]=float(c); return float(c)
        child_ys=[self._layout(c,col+1) for c in node.children]
        cy=sum(child_ys)/len(child_ys)
        self._pos[id(node)]=(node.depth()*self.X,-cy*self.Y); return cy

    def _emit(self, node) -> str:
        if node.kind=='var':
            lbl=node.label
            if lbl in self._varid: return self._varid[lbl]
            nid=self._nid('I')
            x,y=self._pos[id(node)]
            # Use logiTikz.sty input style  
            self._nodes.append(
                f"  \\node[lgin] ({nid}) at ({x+2:.3f}cm,{y:.3f}cm) {{${lbl}$}};")
            self._wires.append(f" \\draw[lgwire] ({nid}.south) -- ++(0,-6);")
            self._varid[lbl]=nid; return nid

        child_ids=[self._emit(c) for c in node.children]
        nid=self._nid('G')
        x,y=self._pos[id(node)]
        gt=GATE_TIKZ[node.kind]
        gs=GATE_STYLE[node.kind]
        self._nodes.append(
            f"  \\node[{gt},{gs}] ({nid}) at ({x*3:.3f}cm,{y:.3f}cm) {{}};")

        if node.kind=='not':
            if node.children[0].kind=='var':
                self._wires.append(f"  \\draw[lgwire] ({child_ids[0]}.south) -- ++(0,-6) |- ({nid}.input);")
            else:
                self._wires.append(f"  \\draw[lgwire] ({child_ids[0]}.east) |- ({nid}.input);")
        else:
            for k,cid in enumerate(child_ids,1):
                if (node.children[k-1].kind=='var'):
                    self._wires.append(f"  \\draw[lgwire] ({cid}.south) -- ++(0,-6) |- ({nid}.input {k});")
                else:
                    self._wires.append(f"  \\draw[lgwire] ({cid}.east) -- ++(1,0) |- ({nid}.input {k});")
        return nid

    def build(self, root) -> str:
        dep=root.depth()
        self._layout(root, dep)
        rid=self._emit(root)
        ranc="south" if rid.startswith("I") else "output"
        out_sty="lgout"
        lines=(
            ["\\begin{tikzpicture}[",
             "  use US style logic gates,",
             "  every node/.append style={font=\\small},",
             "]"]
            + self._nodes + self._wires
            + [f"  \\node[{out_sty}, right=1.5cm of {rid}.{ranc}]",
               f"    (lgoutn) {{${self.output}$}};",
               f"  \\draw[lgwireA] ({rid}.{ranc}) -- (lgoutn.west);"]
        )
        return "\n".join(lines) + "\n\\end{tikzpicture}"

def make_lgtikz(expr, output='S'):
    root = Parser(expr).parse()
    g = TikZGen(output=output)
    g._layout(root, root.depth())
    rid = g._emit(root)
    ranc = "south" if rid.startswith("I") else "output"
    lines = (
        ["\\begin{tikzpicture}[",
         "  use US style logic gates,",
         "  every node/.append style={font=\\small},",
         "]"]
        + g._nodes + g._wires
        + [f"  \\node[lgout, right=1.5cm of {rid}.{ranc}]",
           f"    (lgoutn) {{${output}$}};",
           f"  \\draw[lgwireA] ({rid}.{ranc}) -- (lgoutn.west);",
           "\\end{tikzpicture}"]
    )
    return "\n".join(lines)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("equation")
    ap.add_argument("output", nargs="?", default="S")
    ap.add_argument("-o","--out")
    args = ap.parse_args()
    result = make_lgtikz(args.equation, args.output)
    if args.out:
        open(args.out,"w").write(result)
    else:
        print(result)