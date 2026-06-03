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


def layout_separate(np_, nt, pre, post, dx=2.5):
    # logique d'arbre : les transitions sont placées en fonction de leurs connexions aux places
    px = [0.0] * np_
    py = [0.0] * np_
    tx = [0.0] * nt
    ty = [0.0] * nt
    # pre :                   # post :
    # t1 t2 t3|               # t1 t2 t3|
    # 2  0  0 | p1            # 0  1  1 | p1
    # 0  3  0 | p2            # 3  0  0 | p2
    # 0  0  1 | p3            # 1  0  0 | p3
    
    counter_p = 1
    counter_t = 0
    p_next=[0]
    next_t=[0]
    while counter_p < np_ or counter_t < nt:
        if counter_t >= nt:
            break
        for p in p_next:
            t_pre= detect_t_connect(pre,p) # p->t
            #print("de la place p",p," à les transitions t",t_pre)
            if len(t_pre)==1 : # une seule transition après p
                counter_t+=1
                tx[t_pre[0]]=px[p]+dx
                ty[t_pre[0]]=py[p]
                next_t=t_pre
            else : # plusieurs transitions après p
                counter_t+=len(t_pre)
                for i,t in enumerate(t_pre):
                    tx[t]=px[p]+dx
                    ty[t]=py[p]-(len(t_pre)-1)*dx/2 + i*dx
                next_t=t_pre
            #print("transitions mises:",counter_t,"/",nt-1)
        for t in next_t:
            if counter_p >= np_:
                break
            p_post= detect_p_connect(post,t) # t->p
            #print("de la transition t",t," à les places p",p_post)
            if len(p_post)==1 : # une seule place après t
                counter_p+=1
                px[p_post[0]]=tx[t]+dx
                py[p_post[0]]=ty[t]
                p_next=p_post
            else : # plusieurs places après t
                counter_p+=len(p_post)
                #print("places mises:",counter_p,"/",np_)
                for i,p_ in enumerate(p_post):
                    px[p_]=tx[t]+dx
                    py[p_]=ty[t]-(len(p_post)-1)*dx/2 + i*dx
                p_next=p_post
    return tx, ty, px, py

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



# ═══════════════════════════════════════════════════════════════════
#  Détection des structures via P-invariants
# ═══════════════════════════════════════════════════════════════════

def _find_p_invariants(pre, post):
    """
    P-inv
    """
    import math as _m
    nt = len(pre[0]); np_ = len(pre)
    C  = incidence(pre, post)
    # incrémenter les masques de 0 à 2^nt-1 et multiplier les lignes de C par le masque
    previous = []  # pour stocker les p-invariants déjà trouvés et éviter les combinaisons linéaires
    for mask in range(1, 1<<np_):
        x = [0]*np_
        for i in range(np_):
            if mask & (1<<i):
                x[i] = 1
        if all(sum(C[p][t]*x[p] for p in range(np_))==0 for t in range(nt)):
            # ajouter ce p-invariant à la liste
            if sum(x) > 0 and not_combination(x, previous):  # éviter le p-invariant trivial
                previous.append(x)
                yield x

            
def _find_t_invariants(pre, post):
    """
    T-invariants minimaux par élimination de Fourier-Motzkin.
    Retourne les vecteurs entiers y >= 0 tels que C * y = 0
    (avec C = Post - Pre).
    """
    import math as _m
    nt = len(pre[0]); np_ = len(pre)
    C  = incidence(pre, post)
    # incrémenter les masques de 0 à 2^nt-1 et multiplier les colonnes de C par le masque
    previous = []  # pour stocker les t-invariants déjà trouvés et éviter les combinaisons linéaires
    for mask in range(1, 1<<nt):
        y = [0]*nt
        for i in range(nt):
            if mask & (1<<i):
                y[i] = 1
        if all(sum(C[p][t]*y[t] for t in range(nt))==0 for p in range(np_)):
            # ajouter ce t-invariant à la liste
            # éviter le t-invariant trivial et les combinaisons linéaires de t-invariants déjà trouvés
            if sum(y) > 0 and not_combination(y, previous):
                previous.append(y)
                yield y
                
def not_combination(y, invariants):    
    """Vérifie si y est une combinaison linéaire à coefficients entiers positifs des invariants donnés."""
    if not invariants:
        return True

    target = tuple(y)
    invs = [tuple(inv) for inv in invariants if any(inv)]
    if not invs:
        return True

    invs.sort(key=sum, reverse=True)
    memo = {}

    def can_build(rem):
        if rem in memo:
            return memo[rem]
        if all(v == 0 for v in rem):
            memo[rem] = True
            return True
        for inv in invs:
            if all(rem[i] >= inv[i] for i in range(len(rem))):
                next_rem = tuple(rem[i] - inv[i] for i in range(len(rem)))
                if can_build(next_rem):
                    memo[rem] = True
                    return True
        memo[rem] = False
        return False

    return not can_build(target)

# ═══════════════════════════════════════════════════════════════════
#  Layout hiérarchique avec patterns structurels
# ═══════════════════════════════════════════════════════════════════

def layout_hierarchical(np_, nt, pre, post, marking=None, dx=2.5, dy=2.2, dx_cap=1.8):
    
    import sys as _sys
    from collections import deque, defaultdict
    import statistics as _stats
    from statistics import mean
    C=incidence(pre, post)

    tx = [0.0 for _ in range(nt)]
    ty = [0.0 for _ in range(nt)]
    px = [0.0 for _ in range(np_)]
    py = [0.0 for _ in range(np_)]

    px[0] = C[0][0]*dx

    # t-invariants pour détecter les patterns structuraux
    t_invs = _find_t_invariants(pre, post) # [[1,1,1]]
    p_invs = _find_p_invariants(pre, post) # [[1,1,0,0],[0,0,1,1]],[[1,1,1,1]]
    # detecter la division des transitions: si les transitions t1,t2,t3 forment un t-invariant, les placer sur la même ligne
    t_groups = []
    for inv in t_invs:
        #print("t-invariant testé=",inv)
        for t in range(1,nt):
            found = False
            #print("resolution pour t",t)
            if inv[t] == 1:
                group = [i for i in range(nt) if inv[i] == 1]
                #print("group trouvé=",group)
                if group not in t_groups:
                    t_groups.append(group)
                    #print("groupe ajouté")
                found = True 
                if not found:
                    t_groups.append([t])
                    #print("groupe non trouvé pour t=",t)
                
    # print("t_groups",t_groups)
    # placer les transitions par groupes
    if t_groups:
        for i, group in enumerate(t_groups):
            for t in group:
                tx[t] = 2*(t%len(group))*dx
                ty[t] = -2*i*dy
                #print("t",t,"=",tx[t],ty[t])
    else:
        for t in range(nt):
            tx[t] = 2*t*dx
            ty[t] = 0.0
    # placer les places en fonction des p-invariants : si les places p1,p2 forment un p-invariant, les placer sur la même colonne
    p_groups = []
    for inv in p_invs:
        # enlever les cas triviaux : p-invariant de la forme [0,0,0,0] ou [1,1,1,1]
        if sum(inv) == 0 or sum(inv) == np_:
            continue
        found = False
        for p in range(np_):
            if inv[p] == 1:
                group = [i for i in range(np_) if inv[i] == 1]
                if group not in p_groups:
                    p_groups.append(group)
                found = True
        if not found:
            p_groups.append([p])
    # print("p_groups", p_groups)
    # placer les places par groupes
    if p_groups:
        for group in p_groups:
            for j,p in enumerate(group):
                t_p= detect_t_connect(post,p)
                p_t= detect_t_connect(pre,p)
                merged = set(t_p) | set(p_t)
                px[p] = mean([tx[t] for t in merged])
                py[p] = mean([ty[t] for t in merged]) - (sum(C[p][t]*tx[t] for t in range(nt))/2+dx)/dx 
                if len(merged)==4:
                    py[p] = mean([ty[t] for t in merged])
    else:
        for t in range(nt):
            p_t= detect_p_connect(pre,t)
            for i,p in enumerate(p_t):
                # print("transition",t,"possède les places",p_t,"en entrée")
                px[p] = tx[t]-dx
                py[p] = ty[t] + ((len(p_t)-1)/len(p_t))*dy - i*2*dy/len(p_t)
    return tx, ty, px, py

def detect_t_connect(matrice, p):
    """Retourne la liste des transitions qui ont un arc sortant de p."""
    return [t for t in range(len(matrice[0])) if matrice[p][t] > 0]

def detect_p_connect(matrice, t):    
    """Retourne la liste des places qui ont un arc entrant vers t."""
    return [p for p in range(len(matrice)) if matrice[p][t] > 0]

LAYOUTS = {
    "circle":       layout_circle,
    "bipartite":    layout_bipartite,
    "seperate":     layout_separate,
    "force":        layout_force,
    "hierarchical": layout_hierarchical,
}


# ═══════════════════════════════════════════════════════════════════
#  Calculs algebriques
# ═══════════════════════════════════════════════════════════════════

def incidence(pre, post):
    nt=len(pre[0]); np_=len(pre)
    return [[post[p][t]-pre[p][t] for t in range(nt)] for p in range(np_)]

# ═══════════════════════════════════════════════════════════════════
#  Generateur TikZ -> stdout
# ═══════════════════════════════════════════════════════════════════

def generate(pre, post, place_labels, trans_labels, marking, layout, struct):
    nt=len(pre[0]); np_=len(pre)
    pn=[f"p{i}" for i in range(np_)]
    tn=[f"t{i}" for i in range(nt)]

    fn = LAYOUTS.get(layout, layout_circle)
    tx, ty, px, py = fn(np_, nt, pre, post)
    if struct=="V":
        lab="right"
        sens_transitions=",rotate=90, anchor=center"
        aux = px; px = py; py = [-i for i in aux]
        auxt = tx; tx = ty; ty = [-i for i in auxt]  # par defaut, les labels des places sont au-dessus, ceux des transitions en dessous
        bordermax= max(tx)
        bordermin=min(tx)
    if struct=="H":
        lab="above"
        sens_transitions=""
        bordermax= max(ty)
        bordermin=min(ty)

    out = []
    out.append(r"\begin{tikzpicture}[petrinet]")
    out.append(r"  %% Places  (coord. calculees par Python depuis Pre/Post)")
    for i in range(np_):
        out.append(f"  \\node[place,label={lab}:{place_labels[i]}] ({pn[i]}) at ({px[i]},{py[i]}) {{}};")
        if marking[i] > 0:
            out.append(f"  \\petritokens{{{pn[i]}}}{{{marking[i]}}}")
    out.append(r"  %% Transitions")
    for i in range(nt):
        style = "transition"
        out.append(f"  \\node[{style},label=above:{trans_labels[i]}{sens_transitions}] ({tn[i]}) at ({tx[i]},{ty[i]}) {{}};")
    out.append(r"  %% Arcs Pre  P->T")
    for t in range(nt):
        for p in range(np_):
            w=pre[p][t]
            if w>0:
                wopt=f" node[weight]{{{w}}}" if w>1 else ""
                if struct=='H':
                    if abs(tx[t]-px[p])<3:
                        if post[p][t]>0 and tx[t]<px[p]:
                            out.append(f"  \\draw[arc,red] ({pn[p]}) to [bend left] {wopt} ({tn[t]});")
                        else:
                            out.append(f"  \\draw[arc] ({pn[p]}) -- {wopt} ({tn[t]});")
                    else:
                        out.append(f"  \\draw[arc] ({pn[p]}) to [bend left] {wopt} ({tn[t]});") if py[p]>ty[t] else out.append(f"  \\draw[arc] ({pn[p]}) to [bend right] {wopt} ({tn[t]});")
                if struct=='V':
                    if abs(ty[t]-py[p])<3:
                        if post[p][t]>0 and ty[t]>py[p]:
                            out.append(f"  \\draw[arc,red] ({pn[p]}) to [bend left] {wopt} ({tn[t]});")
                        else:
                            out.append(f"  \\draw[arc] ({pn[p]}) -- {wopt} ({tn[t]});")
                    else:
                        out.append(f"  \\draw[arc] ({pn[p]}) to [bend left] {wopt} ({tn[t]});") if tx[t]>px[p] else out.append(f"  \\draw[arc] ({pn[p]}) to [bend right] {wopt} ({tn[t]});")
    out.append(r"  %% Arcs Post T->P")
    for t in range(nt):
        for p in range(np_):
            w=post[p][t]
            if w>0:
                wopt=f" node[weight]{{{w}}}" if w>1 else ""
                if struct=='H':
                    if abs(tx[t]-px[p])<3:
                        if pre[p][t]>0 and tx[t]>px[p]:
                            out.append(f"  \\draw[arc,red] ({tn[t]}) to [bend left] {wopt} ({pn[p]});")
                        else:
                            out.append(f"  \\draw[arc] ({tn[t]}) -- {wopt} ({pn[p]});")
                    else:
                        out.append(f"  \\draw[arc] ({tn[t]}) to [bend left] {wopt} ({pn[p]});") if py[p]>ty[t] else out.append(f"  \\draw[arc] ({tn[t]}) to [bend right] {wopt} ({pn[p]});")
                if struct=='V':
                    if abs(ty[t]-py[p])<3:
                        if pre[p][t]>0 and ty[t]<py[p]:
                            out.append(f"  \\draw[arc,red] ({tn[t]}) to [bend left] {wopt} ({pn[p]});")
                        else:
                            out.append(f"  \\draw[arc] ({tn[t]}) -- {wopt} ({pn[p]});")
                    else:
                        out.append(f"  \\draw[arc] ({tn[t]}) to [bend left] {wopt} ({pn[p]});") if tx[t]>px[p] else out.append(f"  \\draw[arc] ({tn[t]}) to [bend right] {wopt} ({pn[p]});")

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
    p.add_argument("--layout",  default="hierarchical",
                   choices=["circle","bipartite","seperate","force","hierarchical"])
    p.add_argument("--struct", default="H", choices=["H","V"])
    args = p.parse_args()

    pre  = parse_matrix(args.pre)
    post = parse_matrix(args.post)
    nt   = len(pre[0])
    np_  = len(pre)
    struct = args.struct

    pl = parse_list(args.places)  if args.places  else [f"$P_{i+1}$" for i in range(np_)]
    tl = parse_list(args.trans)   if args.trans   else [f"$T_{i+1}$" for i in range(nt)]
    m  = parse_marking(args.marking) if args.marking else [0]*np_

    generate(pre, post, pl, tl, m, args.layout, struct)


if __name__ == "__main__":
    main()