"""
petritikz.py
============
Appele directement depuis un fichier .tex (Windows ET Linux/Mac) :

    \\input{|"python petritikz.py --pre 1,0,0,0;0,1,1,0 --post 0,1,1,0;1,0,0,1
              --places libre,produit,vide,plein
              --trans  produire,consommer
              --marking 1,0,1,0  --layout circle"}

Format des matrices : lignes separees par  ;  valeurs par  ,
    --pre  "1,0,0,0;0,1,1,0"    signifie  [[1,0,0,0],[0,1,1,0]]
    --post "0,1,1,0;1,0,0,1"    signifie  [[0,1,1,0],[1,0,0,1]]

Aucun fichier intermediaire n'est cree.
Python ecrit le tikzpicture sur stdout, LaTeX le lit en temps reel.

Compilation Windows :
    pdflatex -shell-escape -enable-write18 demo_petritikz.tex

Compilation Linux/Mac :
    pdflatex -shell-escape demo_petritikz.tex
"""

import sys
import math
import argparse


# ═══════════════════════════════════════════════════════════════════
#  Parsing des matrices  (format "1,0,0,0;0,1,1,0")
# ═══════════════════════════════════════════════════════════════════

def parse_matrix(s: str) -> list:
    """
    Accepte deux formats sans guillemets JSON :
        "1,0,0,0;0,1,1,0"    -> [[1,0,0,0],[0,1,1,0]]
        "[[1,0],[0,1]]"       -> [[1,0],[0,1]]   (rétro-compatible)
    """
    s = s.strip()
    if s.startswith("["):
        # Format JSON-like : nettoyer et parser manuellement
        s = s.replace("[","").replace("]","")
        rows = [r for r in s.split(";") if r.strip()]
        if not rows:
            # Tout sur une ligne séparé par virgule (1 transition)
            return [[int(x) for x in s.split(",") if x.strip()]]
        return [[int(x) for x in r.split(",") if x.strip()] for r in rows]
    else:
        # Format natif : "1,0,0,0;0,1,1,0"
        rows = [r.strip() for r in s.split(";") if r.strip()]
        return [[int(x) for x in r.split(",") if x.strip()] for r in rows]


def parse_list(s: str) -> list:
    """'libre,produit,vide,plein' -> ['libre','produit','vide','plein']"""
    return [x.strip() for x in s.split(",") if x.strip()]


def parse_marking(s: str) -> list:
    """'1,0,1,0' -> [1,0,1,0]"""
    return [int(x) for x in s.split(",") if x.strip()]


# ═══════════════════════════════════════════════════════════════════
#  Layouts : Pre/Post -> coordonnees (x, y)
# ═══════════════════════════════════════════════════════════════════

def layout_circle(np_, nt, *_):
    px = [round(3.5*math.cos(math.pi/2 + 2*math.pi*i/np_), 3) for i in range(np_)]
    py = [round(3.5*math.sin(math.pi/2 + 2*math.pi*i/np_), 3) for i in range(np_)]
    tx = [round(2.0*math.cos(math.pi/2 + math.pi/max(nt,1) + 2*math.pi*i/max(nt,1)), 3) for i in range(nt)]
    ty = [round(2.0*math.sin(math.pi/2 + math.pi/max(nt,1) + 2*math.pi*i/max(nt,1)), 3) for i in range(nt)]
    return px, py, tx, ty


def layout_bipartite(np_, nt, *_):
    px = [0.0] * np_
    py = [round((np_-1) - i*2.0, 3) for i in range(np_)]
    tx = [5.0] * nt
    ty = [round((nt-1) - i*2.0, 3) for i in range(nt)]
    return px, py, tx, ty


def layout_grid(np_, nt, pre, post):
    dx = 2.5; offset = -(np_-1)*dx/2.0
    px = [round(offset + i*dx, 3) for i in range(np_)]
    py = [2.0] * np_
    tx, ty = [], []
    for ti in range(nt):
        linked = [pi for pi in range(np_) if pre[ti][pi]>0 or post[ti][pi]>0]
        cx = sum(px[pi] for pi in linked)/len(linked) if linked else round(offset+ti*dx, 3)
        tx.append(round(cx, 3)); ty.append(0.0)
    return px, py, tx, ty


def layout_force(np_, nt, pre, post, iters=300):
    px, py, tx, ty = layout_circle(np_, nt)
    pos = [[px[i], py[i]] for i in range(np_)] + [[tx[i], ty[i]] for i in range(nt)]
    n = np_+nt
    edges = [(pi, np_+ti) for ti in range(nt) for pi in range(np_)
             if pre[ti][pi]>0 or post[ti][pi]>0]
    k, dt, cool = 2.5, 0.5, 0.98
    for _ in range(iters):
        d_ = [[0.0,0.0] for _ in range(n)]
        for i in range(n):
            for j in range(i+1, n):
                dx=pos[i][0]-pos[j][0]; dy=pos[i][1]-pos[j][1]
                dist=math.hypot(dx,dy) or 1e-4; f=k*k/dist
                d_[i][0]+=f*dx/dist; d_[j][0]-=f*dx/dist
                d_[i][1]+=f*dy/dist; d_[j][1]-=f*dy/dist
        for (i,j) in edges:
            dx=pos[i][0]-pos[j][0]; dy=pos[i][1]-pos[j][1]
            dist=math.hypot(dx,dy) or 1e-4; f=dist*dist/k
            d_[i][0]-=f*dx/dist; d_[j][0]+=f*dx/dist
            d_[i][1]-=f*dy/dist; d_[j][1]+=f*dy/dist
        for i in range(n):
            mag=math.hypot(d_[i][0],d_[i][1]) or 1e-4; s=min(mag,dt)
            pos[i][0]+=d_[i][0]/mag*s; pos[i][1]+=d_[i][1]/mag*s
        dt*=cool
    cx=sum(p[0] for p in pos)/n; cy=sum(p[1] for p in pos)/n
    pos=[[round(p[0]-cx,3),round(p[1]-cy,3)] for p in pos]
    return [p[0] for p in pos[:np_]], [p[1] for p in pos[:np_]], \
           [p[0] for p in pos[np_:]], [p[1] for p in pos[np_:]]


LAYOUTS = {
    "circle":    layout_circle,
    "bipartite": layout_bipartite,
    "grid":      layout_grid,
    "force":     layout_force,
}


# ═══════════════════════════════════════════════════════════════════
#  Calculs algebriques
# ═══════════════════════════════════════════════════════════════════

def incidence(pre, post):
    nt=len(pre); np_=len(pre[0])
    return [[post[t][p]-pre[t][p] for p in range(np_)] for t in range(nt)]


def enabled(pre, marking):
    np_=len(marking)
    return [all(marking[p]>=pre[t][p] for p in range(np_)) for t in range(len(pre))]


# ═══════════════════════════════════════════════════════════════════
#  Generateur TikZ -> stdout
# ═══════════════════════════════════════════════════════════════════

def generate(pre, post, place_labels, trans_labels, marking, layout):
    nt=len(pre); np_=len(pre[0])
    pn=[f"p{i}" for i in range(np_)]
    tn=[f"t{i}" for i in range(nt)]

    fn = LAYOUTS.get(layout, layout_circle)
    px, py, tx, ty = fn(np_, nt, pre, post)
    activ = enabled(pre, marking)

    out = []
    out.append(r"\begin{tikzpicture}[petrinet]")
    out.append(r"  %% Places  (coord. calculees par Python depuis Pre/Post)")
    for i in range(np_):
        out.append(f"  \\node[place,label=above:{place_labels[i]}] ({pn[i]}) at ({px[i]},{py[i]}) {{}};")
        if marking[i] > 0:
            out.append(f"  \\petritokens{{{pn[i]}}}{{{marking[i]}}}")
    out.append(r"  %% Transitions")
    for i in range(nt):
        style = "enabled transition" if activ[i] else "transition"
        out.append(f"  \\node[{style},label=below:{trans_labels[i]}] ({tn[i]}) at ({tx[i]},{ty[i]}) {{}};")
    out.append(r"  %% Arcs Pre  P->T")
    for t in range(nt):
        for p in range(np_):
            w=pre[t][p]
            if w>0:
                wopt=f" node[weight]{{{w}}}" if w>1 else ""
                out.append(f"  \\draw[arc] ({pn[p]}) --{wopt} ({tn[t]});")
    out.append(r"  %% Arcs Post T->P")
    for t in range(nt):
        for p in range(np_):
            w=post[t][p]
            if w>0:
                wopt=f" node[weight]{{{w}}}" if w>1 else ""
                out.append(f"  \\draw[arc] ({tn[t]}) --{wopt} ({pn[p]});")
    out.append(r"\end{tikzpicture}")
    sys.stdout.write("\n".join(out)+"\n")
    sys.stdout.flush()


# ═══════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pre",     required=True,
                   help="Matrice Pre :  lignes separees par ; valeurs par ,\n"
                        "  ex: 1,0,0,0;0,1,1,0")
    p.add_argument("--post",    required=True,
                   help="Matrice Post : meme format")
    p.add_argument("--places",  default="",
                   help="Labels places separes par virgule : libre,produit,vide,plein")
    p.add_argument("--trans",   default="",
                   help="Labels transitions : produire,consommer")
    p.add_argument("--marking", default="",
                   help="Marquage initial : 1,0,1,0")
    p.add_argument("--layout",  default="circle",
                   choices=["circle","bipartite","grid","force"])
    args = p.parse_args()

    pre  = parse_matrix(args.pre)
    post = parse_matrix(args.post)
    nt   = len(pre)
    np_  = len(pre[0])

    pl = parse_list(args.places)  if args.places  else [f"p{i}" for i in range(np_)]
    tl = parse_list(args.trans)   if args.trans   else [f"t{i}" for i in range(nt)]
    m  = parse_marking(args.marking) if args.marking else [0]*np_

    generate(pre, post, pl, tl, m, args.layout)


if __name__ == "__main__":
    main()