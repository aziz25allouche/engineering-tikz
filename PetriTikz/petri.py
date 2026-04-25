"""
PetriTikz — Tracé automatique de réseaux de Petri depuis Pre/Post
==================================================================
Le schéma TikZ est entièrement calculé par Python à partir des
matrices Pre et Post :  coordonnées, arcs, marquage, activabilité.

Usage rapide
------------
    from petritikz import PetriNet, Place, Transition, generate_tikz

    places      = [Place("p1", tokens=1, label="libre"),
                   Place("p2", label="produit"),
                   Place("p3", tokens=1, label="vide"),
                   Place("p4", label="plein")]
    transitions = [Transition("t1", label="produire"),
                   Transition("t2", label="consommer")]
    pre  = [[1,0,0,0], [0,1,1,0]]
    post = [[0,1,1,0], [1,0,0,1]]

    net  = PetriNet("Prod/Conso", places, transitions, pre, post)
    tikz = generate_tikz(net, layout="circle")  # code TikZ prêt à coller
    print(tikz)

Build complet (génère tous les fragments pour le demo)
------------------------------------------------------
    python petritikz.py --build-demo
    pdflatex demo_petritikz.tex

CLI
---
    python petritikz.py --example producer --layout circle  --output out.tex
    python petritikz.py --example mutex    --layout bipartite
    python petritikz.py --json mon_reseau.json --layout grid
    python petritikz.py --tikz-only   # fragment seul, sans \\documentclass
"""

import argparse
import math
import json
import os
from dataclasses import dataclass
from typing import Optional


# ═══════════════════════════════════════════════════════════════════
#  Structures de données
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Place:
    name:   str
    tokens: int = 0
    x:      float = 0.0
    y:      float = 0.0
    label:  Optional[str] = None


@dataclass
class Transition:
    name:  str
    x:     float = 0.0
    y:     float = 0.0
    label: Optional[str] = None


@dataclass
class PetriNet:
    name:        str
    places:      list
    transitions: list
    pre:         list   # pre[t][p]  — arc P→T
    post:        list   # post[t][p] — arc T→P
    marking:     Optional[list] = None

    def __post_init__(self):
        if self.marking is None:
            self.marking = [p.tokens for p in self.places]

    # ── Algèbre ─────────────────────────────────────────────────────

    def incidence_matrix(self):
        """C = Post − Pre   (ligne = transition, colonne = place)"""
        np_ = len(self.places)
        return [[self.post[t][p] - self.pre[t][p]
                 for p in range(np_)]
                for t in range(len(self.transitions))]

    def enabled_transitions(self, marking=None):
        """Renvoie une liste de bool : t activable ⟺ marking ≥ pre[t]"""
        m = marking if marking is not None else self.marking
        return [all(m[p] >= self.pre[t][p] for p in range(len(self.places)))
                for t in range(len(self.transitions))]

    def fire(self, t_idx: int, marking=None):
        """Franchit t_idx et retourne le nouveau marquage."""
        m = list(marking if marking is not None else self.marking)
        if not self.enabled_transitions(m)[t_idx]:
            raise ValueError(
                f"Transition {self.transitions[t_idx].name} non activable "
                f"depuis {m}"
            )
        C = self.incidence_matrix()
        return [m[p] + C[t_idx][p] for p in range(len(self.places))]

    def reachability_set(self, max_steps: int = 500):
        """Ensemble d'accessibilité par BFS (limité à max_steps)."""
        visited, queue = set(), [tuple(self.marking)]
        visited.add(tuple(self.marking))
        for _ in range(max_steps):
            if not queue:
                break
            cur = list(queue.pop(0))
            for t in range(len(self.transitions)):
                if self.enabled_transitions(cur)[t]:
                    nxt = tuple(self.fire(t, cur))
                    if nxt not in visited:
                        visited.add(nxt)
                        queue.append(list(nxt))
        return [list(m) for m in visited]


# ═══════════════════════════════════════════════════════════════════
#  Algorithmes de layout  (entrée : Pre/Post → sortie : (x, y))
# ═══════════════════════════════════════════════════════════════════

def _layout_circle(net: PetriNet):
    """
    Places sur un grand cercle, transitions sur un cercle intérieur.
    Angle de départ des transitions décalé de π/n pour intercaler
    chaque transition entre deux places adjacentes.
    """
    np_ = len(net.places)
    nt  = len(net.transitions)
    R_p, R_t = 3.5, 2.0

    for i, p in enumerate(net.places):
        a = 2 * math.pi * i / np_ + math.pi / 2   # commence en haut
        p.x = round(R_p * math.cos(a), 3)
        p.y = round(R_p * math.sin(a), 3)

    for i, t in enumerate(net.transitions):
        a = 2 * math.pi * i / max(nt, 1) + math.pi / 2 + math.pi / max(nt, 1)
        t.x = round(R_t * math.cos(a), 3)
        t.y = round(R_t * math.sin(a), 3)


def _layout_bipartite(net: PetriNet):
    """
    Deux colonnes verticales centrées :
      • places      à x = 0
      • transitions à x = 5
    Chaque colonne est centrée verticalement.
    """
    np_ = len(net.places)
    nt  = len(net.transitions)

    # centrage vertical : espacement de 2.0 entre nœuds
    p_top = (np_ - 1) * 1.0   # milieu à y=0
    t_top = (nt  - 1) * 1.0

    for i, p in enumerate(net.places):
        p.x = 0.0
        p.y = round(p_top - i * 2.0, 3)

    for i, t in enumerate(net.transitions):
        t.x = 5.0
        t.y = round(t_top - i * 2.0, 3)


def _layout_grid(net: PetriNet):
    """
    Grille bipartite : places sur la rangée haute, transitions sur
    la rangée basse, chaque transition alignée sous son barycentre
    de places connectées (Pre ∪ Post).
    """
    np_ = len(net.places)
    nt  = len(net.transitions)
    dx  = 2.5

    # Places : rangée haute
    offset_p = -(np_ - 1) * dx / 2
    for i, p in enumerate(net.places):
        p.x = round(offset_p + i * dx, 3)
        p.y = 2.0

    # Transitions : centrées sous les places qu'elles touchent
    for ti, t in enumerate(net.transitions):
        connected = [pi for pi in range(np_)
                     if net.pre[ti][pi] > 0 or net.post[ti][pi] > 0]
        if connected:
            cx = sum(net.places[pi].x for pi in connected) / len(connected)
        else:
            cx = round(offset_p + ti * dx, 3)
        t.x = round(cx, 3)
        t.y = 0.0


def _layout_force(net: PetriNet, iterations: int = 300):
    """
    Disposition par simulation de forces (Fruchterman-Reingold simplifié).
    Les nœuds reliés s'attirent, tous se repoussent mutuellement.
    On part d'un layout circulaire comme initialisation.

    Paramètres heuristiques :
        k      : distance idéale entre nœuds
        dt     : pas de temps
        cooling: facteur de refroidissement par itération
    """
    nodes = net.places + net.transitions
    n = len(nodes)
    if n == 0:
        return

    # Initialisation circulaire
    _layout_circle(net)
    pos = [[nd.x, nd.y] for nd in nodes]

    # Arêtes : liste de paires (i, j) avec i = indice dans `nodes`
    np_ = len(net.places)
    edges = []
    for ti, t in enumerate(net.transitions):
        ti_idx = np_ + ti
        for pi in range(np_):
            if net.pre[ti][pi] > 0 or net.post[ti][pi] > 0:
                edges.append((pi, ti_idx))

    k  = 2.5                     # distance idéale
    dt = 0.5
    cooling = 0.98

    for _ in range(iterations):
        disp = [[0.0, 0.0] for _ in range(n)]

        # Répulsion entre toutes les paires
        for i in range(n):
            for j in range(i + 1, n):
                dx = pos[i][0] - pos[j][0]
                dy = pos[i][1] - pos[j][1]
                dist = math.hypot(dx, dy) or 0.01
                f = k * k / dist
                disp[i][0] += f * dx / dist
                disp[i][1] += f * dy / dist
                disp[j][0] -= f * dx / dist
                disp[j][1] -= f * dy / dist

        # Attraction le long des arêtes
        for (i, j) in edges:
            dx = pos[i][0] - pos[j][0]
            dy = pos[i][1] - pos[j][1]
            dist = math.hypot(dx, dy) or 0.01
            f = dist * dist / k
            disp[i][0] -= f * dx / dist
            disp[i][1] -= f * dy / dist
            disp[j][0] += f * dx / dist
            disp[j][1] += f * dy / dist

        # Déplacement limité par dt
        for i in range(n):
            dmag = math.hypot(disp[i][0], disp[i][1]) or 0.01
            step = min(dmag, dt)
            pos[i][0] += disp[i][0] / dmag * step
            pos[i][1] += disp[i][1] / dmag * step

        dt *= cooling

    # Centrage
    cx = sum(p[0] for p in pos) / n
    cy = sum(p[1] for p in pos) / n
    for i, nd in enumerate(nodes):
        nd.x = round(pos[i][0] - cx, 3)
        nd.y = round(pos[i][1] - cy, 3)


_LAYOUTS = {
    "circle":    _layout_circle,
    "bipartite": _layout_bipartite,
    "grid":      _layout_grid,
    "force":     _layout_force,
}


# ═══════════════════════════════════════════════════════════════════
#  Générateur TikZ
# ═══════════════════════════════════════════════════════════════════

def _w(weight: int, show: bool) -> str:
    """Retourne le node[weight]{...} ou '' si poids trivial."""
    if not show or weight == 1:
        return ""
    return f"node[weight]{{{weight}}} "


def generate_tikz(net: PetriNet,
                  layout:       str  = "circle",
                  show_weights: bool = True) -> str:
    """
    Génère le code TikZ COMPLET depuis pre/post.
    Aucune coordonnée n'est fournie manuellement.

    Étapes internes :
      1. Calcule les coordonnées (x,y) via l'algorithme `layout`
      2. Détermine les transitions activables depuis le marquage courant
      3. Émet les \\node place / transition avec positions et styles
      4. Émet les \\draw[arc] pour chaque entrée non nulle de Pre et Post
    """
    # ── 1. Layout automatique ──────────────────────────────────────
    _LAYOUTS.get(layout, _layout_circle)(net)

    # ── 2. Activabilité ───────────────────────────────────────────
    enabled = net.enabled_transitions()

    lines = [
        f"% Généré par petritikz.py  |  layout={layout}",
        f"% Pre  = {net.pre}",
        f"% Post = {net.post}",
        r"\begin{tikzpicture}[petrinet]",
        "",
        "  % ── Places (coordonnées calculées depuis Pre/Post) ──────",
    ]

    # ── 3a. Nœuds places ──────────────────────────────────────────
    for i, p in enumerate(net.places):
        lbl = p.label or p.name
        tok = f",tokens={net.marking[i]}" if net.marking[i] > 0 else ""
        lines.append(
            f"  \\node[place,label=above:{{{lbl}}}{tok}]"
            f"  ({p.name}) at ({p.x},{p.y}) {{}};"
        )

    lines += ["", "  % ── Transitions ──────────────────────────────────────"]

    # ── 3b. Nœuds transitions ─────────────────────────────────────
    for i, t in enumerate(net.transitions):
        lbl    = t.label or t.name
        en_opt = ",enabled" if enabled[i] else ""
        lines.append(
            f"  \\node[transition{en_opt},label=below:{{{lbl}}}]"
            f"  ({t.name}) at ({t.x},{t.y}) {{}};"
        )

    lines += ["", "  % ── Arcs Pre  P→T  (lus depuis net.pre) ────────────"]

    # ── 4a. Arcs Pre ──────────────────────────────────────────────
    for ti, t in enumerate(net.transitions):
        for pi, p in enumerate(net.places):
            w = net.pre[ti][pi]
            if w > 0:
                lines.append(
                    f"  \\draw[arc] ({p.name}) -- {_w(w, show_weights)}({t.name});"
                )

    lines += ["", "  % ── Arcs Post T→P  (lus depuis net.post) ───────────"]

    # ── 4b. Arcs Post ─────────────────────────────────────────────
    for ti, t in enumerate(net.transitions):
        for pi, p in enumerate(net.places):
            w = net.post[ti][pi]
            if w > 0:
                lines.append(
                    f"  \\draw[arc] ({t.name}) -- {_w(w, show_weights)}({p.name});"
                )

    lines += ["", r"\end{tikzpicture}"]
    return "\n".join(lines)


def generate_full_document(net: PetriNet, layout: str = "circle") -> str:
    """Document LaTeX autonome : schéma + matrices + analyse."""
    tikz  = generate_tikz(net, layout=layout)
    C     = net.incidence_matrix()
    en    = net.enabled_transitions()
    np_   = len(net.places)
    nt    = len(net.transitions)

    def mat_tex(m):
        rows = " \\\\\n".join(
            "    " + " & ".join(str(m[t][p]) for p in range(np_))
            for t in range(nt)
        )
        return r"\begin{pmatrix}" + "\n" + rows + "\n" + r"\end{pmatrix}"

    en_names = ", ".join(net.transitions[i].name
                         for i, e in enumerate(en) if e) or r"\emptyset"
    m0_str   = ", ".join(str(v) for v in net.marking)

    return rf"""\documentclass[a4paper,11pt]{{article}}
\usepackage{{petritikz}}
\usepackage{{amsmath}}
\title{{\textbf{{Réseau de Petri}} --- {net.name}}}
\author{{PetriTikz Generator}}
\date{{\today}}
\begin{{document}}
\maketitle

\section*{{Schéma (layout : {layout})}}

\begin{{center}}
{tikz}
\end{{center}}

\section*{{Matrices Pre et Post}}
\[
  \text{{Pre}}  = {mat_tex(net.pre)}
  \qquad
  \text{{Post}} = {mat_tex(net.post)}
\]

\section*{{Matrice d'incidence}}
\[
  C = \text{{Post}} - \text{{Pre}} = {mat_tex(C)}
\]

\section*{{Marquage initial et activabilité}}
\[
  M_0 = ({m0_str})
  \qquad
  \mathcal{{T}}_\text{{act}} = \{{ {en_names} \}}
\]

\end{{document}}
"""


# ═══════════════════════════════════════════════════════════════════
#  Exemples intégrés
# ═══════════════════════════════════════════════════════════════════

def example_producer_consumer() -> PetriNet:
    """
    Réseau producteur–consommateur.

    Seules les matrices Pre et Post sont définies par l'utilisateur.
    Toutes les coordonnées et arcs TikZ sont calculés par generate_tikz().

        Pre  = [[1,0,0,0],   # t1 consomme p1 (libre)
                [0,1,1,0]]   # t2 consomme p2 (produit) + p3 (vide)

        Post = [[0,1,1,0],   # t1 produit p2 + p3
                [1,0,0,1]]   # t2 produit p1 (libre) + p4 (plein)
    """
    places = [
        Place("p1", tokens=1, label="libre"),
        Place("p2", tokens=0, label="produit"),
        Place("p3", tokens=1, label="vide"),
        Place("p4", tokens=0, label="plein"),
    ]
    transitions = [
        Transition("t1", label="produire"),
        Transition("t2", label="consommer"),
    ]
    pre  = [[1, 0, 0, 0],
            [0, 1, 1, 0]]
    post = [[0, 1, 1, 0],
            [1, 0, 0, 1]]
    return PetriNet("Producteur–Consommateur", places, transitions, pre, post)


def example_mutex() -> PetriNet:
    """
    Exclusion mutuelle entre deux processus.

        Pre  = [[1,0,1,0,0],
                [0,0,0,1,0],
                [0,1,1,0,0],
                [0,0,0,0,1]]

        Post = [[0,0,0,1,0],
                [1,0,1,0,0],
                [0,0,0,0,1],
                [0,1,1,0,0]]
    """
    places = [
        Place("p1", tokens=1, label="attente 1"),
        Place("p2", tokens=1, label="attente 2"),
        Place("p3", tokens=1, label="mutex"),
        Place("p4", tokens=0, label="SC 1"),
        Place("p5", tokens=0, label="SC 2"),
    ]
    transitions = [
        Transition("t1", label="entrer 1"),
        Transition("t2", label="sortir 1"),
        Transition("t3", label="entrer 2"),
        Transition("t4", label="sortir 2"),
    ]
    pre  = [[1,0,1,0,0],
            [0,0,0,1,0],
            [0,1,1,0,0],
            [0,0,0,0,1]]
    post = [[0,0,0,1,0],
            [1,0,1,0,0],
            [0,0,0,0,1],
            [0,1,1,0,0]]
    return PetriNet("Exclusion Mutuelle", places, transitions, pre, post)


# ═══════════════════════════════════════════════════════════════════
#  Chargement JSON
# ═══════════════════════════════════════════════════════════════════

def load_from_json(path: str) -> PetriNet:
    """
    Format JSON attendu :
    {
      "name": "Mon réseau",
      "places":      [{"name":"p1","tokens":1,"label":"libre"}, ...],
      "transitions": [{"name":"t1","label":"produire"}, ...],
      "pre":  [[1,0,...], ...],
      "post": [[0,1,...], ...]
    }
    """
    with open(path) as f:
        d = json.load(f)
    places      = [Place(**p)      for p in d["places"]]
    transitions = [Transition(**t) for t in d["transitions"]]
    return PetriNet(
        name=d.get("name", "Réseau"),
        places=places,
        transitions=transitions,
        pre=d["pre"],
        post=d["post"],
        marking=d.get("marking"),
    )


# ═══════════════════════════════════════════════════════════════════
#  Build demo  — génère tous les fragments TikZ pour demo_petritikz.tex
# ═══════════════════════════════════════════════════════════════════

def build_demo(outdir: str = "."):
    """
    Génère dans `outdir` tous les fichiers .tex inclus par demo_petritikz.tex.
    Aucune coordonnée n'est écrite à la main dans le demo.
    """
    os.makedirs(outdir, exist_ok=True)

    tasks = [
        ("fig_producer_circle",    example_producer_consumer, "circle"),
        ("fig_producer_bipartite", example_producer_consumer, "bipartite"),
        ("fig_producer_grid",      example_producer_consumer, "grid"),
        ("fig_producer_force",     example_producer_consumer, "force"),
        ("fig_mutex_bipartite",    example_mutex,             "bipartite"),
        ("fig_mutex_circle",       example_mutex,             "circle"),
        ("fig_mutex_force",        example_mutex,             "force"),
    ]

    for fname, net_fn, layout in tasks:
        net  = net_fn()
        tikz = generate_tikz(net, layout=layout)
        path = os.path.join(outdir, fname + ".tex")
        with open(path, "w") as f:
            f.write(tikz)
        print(f"  [build] {path}")

    # --- Données analytiques pour le demo (producer) ---------------
    net = example_producer_consumer()
    C   = net.incidence_matrix()
    en  = net.enabled_transitions()

    # franchissements successifs jusqu'à épuisement ou cycle
    history = [list(net.marking)]
    m = list(net.marking)
    t_seq = []
    for _ in range(4):
        act = [i for i, e in enumerate(net.enabled_transitions(m)) if e]
        if not act:
            break
        ti = act[0]
        m  = net.fire(ti, m)
        t_seq.append(net.transitions[ti].name)
        history.append(m)
        if tuple(m) == tuple(net.marking):
            break   # cycle détecté

    data_path = os.path.join(outdir, "data_producer.py")
    with open(data_path, "w") as f:
        f.write(f"PRE      = {net.pre}\n")
        f.write(f"POST     = {net.post}\n")
        f.write(f"C        = {C}\n")
        f.write(f"M0       = {net.marking}\n")
        f.write(f"ENABLED  = {[net.transitions[i].name for i,e in enumerate(en) if e]}\n")
        f.write(f"HISTORY  = {history}\n")
        f.write(f"T_SEQ    = {t_seq}\n")
    print(f"  [build] {data_path}")

    # --- Données mutex ----------------------------------------------
    net2 = example_mutex()
    C2   = net2.incidence_matrix()
    en2  = net2.enabled_transitions()
    m1   = net2.fire(0)   # fire t1
    en_after = net2.enabled_transitions(m1)

    data2_path = os.path.join(outdir, "data_mutex.py")
    with open(data2_path, "w") as f:
        f.write(f"PRE         = {net2.pre}\n")
        f.write(f"POST        = {net2.post}\n")
        f.write(f"C           = {C2}\n")
        f.write(f"M0          = {net2.marking}\n")
        f.write(f"ENABLED_M0  = {[net2.transitions[i].name for i,e in enumerate(en2) if e]}\n")
        f.write(f"M1          = {m1}\n")
        f.write(f"ENABLED_M1  = {[net2.transitions[i].name for i,e in enumerate(en_after) if e]}\n")
    print(f"  [build] {data2_path}")

    print("\n  Prêt. Compilez maintenant avec :")
    print("    pdflatex demo_petritikz.tex")


# ═══════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="PetriTikz — Tracé automatique depuis matrices Pre/Post",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--example",
                        choices=["producer", "mutex"],
                        default="producer")
    parser.add_argument("--json",   help="Fichier JSON décrivant le réseau")
    parser.add_argument("--layout",
                        choices=["circle", "bipartite", "grid", "force"],
                        default="circle")
    parser.add_argument("--output", default="output.tex")
    parser.add_argument("--tikz-only", action="store_true",
                        help="Émet uniquement le bloc tikzpicture")
    parser.add_argument("--build-demo", action="store_true",
                        help="Génère tous les fragments pour demo_petritikz.tex")
    args = parser.parse_args()

    if args.build_demo:
        build_demo(".")
        return

    if args.json:
        net = load_from_json(args.json)
    elif args.example == "mutex":
        net = example_mutex()
    else:
        net = example_producer_consumer()

    content = (generate_tikz(net, layout=args.layout)
               if args.tikz_only
               else generate_full_document(net, layout=args.layout))

    with open(args.output, "w") as f:
        f.write(content)

    # Résumé console
    en = net.enabled_transitions()
    print(f"[PetriTikz] → {args.output}  (layout={args.layout})")
    print(f"  Réseau     : {net.name}")
    print(f"  Places     : {[p.name for p in net.places]}")
    print(f"  Transitions: {[t.name for t in net.transitions]}")
    print(f"  Marquage M0: {net.marking}")
    print(f"  Activables : {[net.transitions[i].name for i,e in enumerate(en) if e]}")
    print(f"  Matrice C  : {net.incidence_matrix()}")


if __name__ == "__main__":
    main()