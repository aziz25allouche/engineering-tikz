#!/usr/bin/env python3
r"""
logique_karnaugh.py  --  Solveur de Karnaugh pour karnaughTikz
Appele par \kvautogroup via \write18.

Usage :
  python3 logique_karnaugh.py <nvars> "<vals>"

<nvars>  = 2, 3 ou 4
<vals>   = valeurs separees par virgules en ordre MINTERM (0..2^n-1)
           ex: "1,0,0,1"  ou  "1,1,0,0,1,X,0,X"

Sortie : une suite de \kvgroup[color]{indices} sur stdout,
         directement \input-able par LaTeX.

ALGORITHME :
  1. Génère TOUS les rectangles Karnaugh valides (tailles 2^k × 2^j)
  2. Les trient par TAILLE DÉCROISSANTE pour favoriser les grands groupements
  3. Utilise un algorithme GREEDY : prend le plus grand rectangle qui couvre
     des 1s non couverts, jusqu'à couvrir tous les 1s
  4. Génère des commandes LaTeX \kvgroup[color]{indices} colorées
r"""

import sys

# ─────────────────────────────────────────────────────────────────────────────
# TABLES DE CONVERSION - CODE GRAY
# ─────────────────────────────────────────────────────────────────────────────
# Pour une grille Karnaugh, l'ordre Gray est essentiel pour que les cellules
# adjacentes en affichage soient aussi adjacentes en logique (différent d'une bin).
# Les tables permettent de convertir entre :
#   - positon_affichage : index (0,1,2,3) comme affiché dans la grille
#   - indice_minterm : numéro du minterm en ordre étendu

GRAY2 = [0, 1, 3, 2]          # position affichage -> indice Gray (0->0, 1->1, 2->3, 3->2)
GRAY2INV = {0:0, 1:1, 3:2, 2:3}  # indice Gray -> position affichage (inverse)

def minterm_to_pos(m, nvars):
    """
    Convertit un INDICE MINTERM en POSITION AFFICHAGE (row, col) dans la grille.
    
    MINTERM = indice du terme 0..2^n-1 dans l'ordre étendu
    POSITION = où la cellule s'affiche réellement (avec ordre Gray)
    
    Exemple pour 4 variables (4x4 grille) :
      minterm 5 -> cherche sa ligne et colonne dans la grille à affichage Gray
    
    Formules :
      - nvars=2 : grille 2x2, conversion directe
      - nvars=3 : grille 2x4 (lignes simples, colonnes en Gray)
      - nvars=4 : grille 4x4 (lignes ET colonnes en Gray, le plus complexe)
    """
    if nvars == 2:
        # Grille 2x2 : m en décimal -> (ligne, colonne)
        row = m // 2      # Première moitié (0,1) -> ligne 0 ; deuxième moitié (2,3) -> ligne 1
        col = m % 2       # Modulo 2 -> colonne 0 ou 1
    elif nvars == 3:
        # Grille 2x4 : m en décimal -> (ligne, colonne Gray)
        row = m // 4      # Les 4 premiers minterms (0,1,2,3) -> ligne 0 ; les 4 suivants -> ligne 1
        col = GRAY2INV[m % 4]  # Les 4 minterms par groupe de 2 bits se convertissent en colonne Gray
    else:  # nvars == 4
        # Grille 4x4 : m en décimal -> (ligne Gray, colonne Gray)
        # Les 16 minterms sont organisés : 4 bits = (2 bits ligne Gray)(2 bits colonne Gray)
        row = GRAY2INV[m // 4]      # Bits hauts (4-7) -> ligne Gray
        col = GRAY2INV[m % 4]       # Bits bas (0-3) -> colonne Gray
    return row, col

def pos_to_minterm(row, col, nvars):
    """
    Convertit une POSITION AFFICHAGE (row, col) en INDICE MINTERM.
    C'est l'inverse de minterm_to_pos().
    
    Prend une cellule à la position d'affichage (row, col) et retourne
    son numéro de minterm dans l'ordre étendu.
    
    Formules (inverses de minterm_to_pos) :
      - nvars=2 : conversion directe
      - nvars=3 : ligne simple, colonne Gray inversée
      - nvars=4 : ligne et colonne Gray inversées
    """
    if nvars == 2:
        # m = row*2 + col  (ligne 0-1, colonne 0-1 -> minterm 0-3)
        return row * 2 + col
    elif nvars == 3:
        # m = row*4 + GRAY2[col]  (la colonne Gray est convertie en indice minterm)
        return row * 4 + GRAY2[col]
    else:  # nvars == 4
        # m = GRAY2[row]*4 + GRAY2[col]  (les deux lignes et colonnes sont Gray)
        return GRAY2[row] * 4 + GRAY2[col]

def get_neighbors(m, nvars, nc, nr):
    """
    Retourne les VOISINS IMMÉDIATS d'un minterm dans la grille.
    
    Considère la grille comme TORIQUE (les bords s'enroulent) :
      - La ligne du bas est voisine de la ligne du haut
      - La colonne droite est voisine de la colonne gauche
    
    Une cellule a 4 voisins (haut, bas, gauche, droite).
    
    Paramètres :
      m : indice minterm
      nvars : nombre de variables (2, 3 ou 4)
      nc : nombre de colonnes
      nr : nombre de lignes
    
    Retour : liste des 4 voisins
    
    Algorithme :
      1. Convertit minterm m en position affichage (row, col)
      2. Ajoute les 4 déplacements (haut, bas, gauche, droite)
      3. Applique modulo pour gestion torique (% nr et % nc)
      4. Reconvertit en minterm
    """
    r, c = minterm_to_pos(m, nvars)
    neighbors = []
    
    # Les 4 déplacements : (delta_row, delta_col)
    for dr, dc in [(0,1), (0,-1), (1,0), (-1,0)]:
        # Applique le déplacement avec modulo pour torique
        nr2 = (r + dr) % nr   # Wrappe verticalement
        nc2 = (c + dc) % nc   # Wrappe horizontalement
        # Reconvertit la nouvelle position en minterm
        neighbors.append(pos_to_minterm(nr2, nc2, nvars))
    
    return neighbors

# ── Génération de tous les groupes possibles ────────────────────────────────

def is_valid_group(indices, nvars, nc, nr):
    """
    Vérifie qu'un ensemble de minterms forme un RECTANGLE VALIDE en Karnaugh.
    
    CONDITIONS POUR UN GROUPE VALIDE :
      1. Doit être un rectangle : hauteur et largeur sont des puissances de 2
      2. Tous les minterms doivent former cette forme rectangulaire
      3. Les lignes et colonnes doivent être CONTIGUËS (ou wrapper toriquement)
    
    Exemples valides :
      - 4 cellules 2x2 contiguës
      - 8 cellules 1x8 (wrap possible)
      - Toute forme 2^i × 2^j
    
    Exemples INVALIDES :
      - L ou autres formes non rectangulaires
      - Cellules isolés
    
    NOTE : Cette fonction n'est plus utilisée dans le nouvel algorithme,
           mais reste pour les tests éventuels.
    """
    if not indices:
        return False
    
    # Convertit tous les minterms en positions d'affichage
    positions = [minterm_to_pos(m, nvars) for m in indices]
    rows = sorted(set(r for r, c in positions))  # Ensemble des lignes uniques
    cols = sorted(set(c for r, c in positions))  # Ensemble des colonnes uniques

    # Vérifie que les dimensions sont des puissances de 2
    def is_pow2(n): return n > 0 and (n & (n-1)) == 0  # Vérifie si n = 2^k
    if not (is_pow2(len(rows)) and is_pow2(len(cols))): 
        return False
    
    # Vérifie le nombre total de cellules = hauteur × largeur
    if len(rows) * len(cols) != len(indices): 
        return False

    # Vérifie la contiguïté torique des lignes et colonnes
    def is_contiguous_toric(lst, total):
        """
        Vérifie qu'une liste d'indices est contiguë (gère le torique).
        
        Cas 1 : Tous les éléments -> valide
        Cas 2 : Contiguïté normale (sans wrap) : max - min = len - 1
        Cas 3 : Contiguïté avec wrap : 0..k puis total-j..total-1
        """
        if len(lst) == total: 
            return True
        
        lst = sorted(lst)
        
        # Cas 2: Contigu normal (sans wrap)
        # Exemple : lst = [1,2,3] total=4 -> 3-1 = 2 = len-1 ✓
        if lst[-1] - lst[0] == len(lst) - 1: 
            return True
        
        # Cas 3: Wrap circulaire valide
        # Les éléments sont disjoints mais contigus en torique
        # Exemple : lst = [0,1,3] total=4 -> wrap en 2,3 et 0,1
        gaps = [lst[i+1] - lst[i] for i in range(len(lst)-1)]
        if all(g == 1 for g in gaps):  # Tous les gaps internes = 1
            # Le gap au wrap (retour à 0) doit être 1 aussi
            wrap_gap = (lst[0] + total) - lst[-1]  # Distance du max au min par wrappe
            return wrap_gap == 1
        
        return False

    # Le groupe est valide si ses lignes ET colonnes sont contiguës toriquement
    return (is_contiguous_toric(rows, nr) and
            is_contiguous_toric(cols, nc))

def generate_all_rectangles(nvars, nc, nr, ones_and_dcs):
    """
    Génère TOUS les rectangles valides possibles dans la grille Karnaugh.
    
    Cette fonction est au CŒUR du nouvel algorithme optimisé. Au lieu de
    tenter aléatoirement des combinaisons, elle énumère SYSTÉMATIQUEMENT
    tous les rectangles 2^i × 2^j possibles, triés par TAILLE DÉCROISSANTE.
    
    C'EST CRUCIAL : examiner les grands rectangles en premier assure que
    l'algorithme greedy trouvera les meilleurs groupements.
    
    Paramètres :
      nvars : nombre de variables (2, 3 ou 4)
      nc : nombre de colonnes (2, 4 ou 4)
      nr : nombre de lignes (2, 2 ou 4)
      ones_and_dcs : ensemble des minterms qui sont '1' ou 'X'
    
    Retour : liste de tuples (taille, ensemble_de_minterms)
             triée par taille DÉCROISSANTE
    
    Algorithme :
      1. Énumère tous les dimensions rectangulaires valides (puissances de 2)
      2. Pour chaque dimension, teste chaque position possible (torique)
      3. Collecte les minterms du rectangle à cette position
      4. Vérifie que tous les minterms sont des '1' ou 'X'
      5. Ajoute le rectangle à la liste
      6. Trie par taille décroissante
    """
    rectangles = []
    
    # Fonction utilitaire : teste si n = 2^k
    def is_pow2(n): return n > 0 and (n & (n-1)) == 0
    
    # ÉTAPE 1 : Énumère toutes les dimensions rectangulaires possibles
    # Exemples pour 4x4 : 16(1x16), 8(1x8), 8(2x4), 4(1x4), 4(2x2), etc.
    dimensions = []
    for height in range(1, nr + 1):
        if is_pow2(height):  # Hauteur doit être 2^k
            for width in range(1, nc + 1):
                if is_pow2(width):  # Largeur doit être 2^k
                    dimensions.append((height, width, height * width))
    
    # ÉTAPE 2 : Trie par taille décroissante (élémentaire pour l'algorithme greedy)
    dimensions.sort(key=lambda x: -x[2])
    
    # ÉTAPE 3 : Pour chaque dimension, énumère toutes ses positions possibles
    for height, width, size in dimensions:
        # Énumère toutes les positions (row, col) du coin supérieur gauche
        # La grille est torique : les rectangles peuvent wrappe sur les bords
        for start_row in range(nr):
            for start_col in range(nc):
                # ÉTAPE 4 : Collecte les minterms du rectangle
                # à partir du coin (start_row, start_col) et dimension height×width
                minterms = []
                for drow in range(height):
                    for dcol in range(width):
                        wrap_c = 'false'
                        wrap_r = 'false'
                        # Wrappe les indices avec modulo (torique)
                        r = (start_row + drow) % nr
                        if start_row + drow>=nr: wrap_r = 'true'
                        c = (start_col + dcol) % nc
                        if start_col + dcol>=nc: wrap_c = 'true'
                        # Convertit position affichage -> minterm
                        m = pos_to_minterm(r, c, nvars)
                        minterms.append(m)
                
                # ÉTAPE 5 : Vérifie que TOUS les minterms sont des '1' ou 'X'
                # Les 'don't cares' (X) peuvent être utilisés pour agrandir les groupes
                if all(m in ones_and_dcs for m in minterms):
                    # ÉTAPE 6 : Ajoute ce rectangle à la liste
                    rectangles.append((size, set(minterms),wrap_r,wrap_c))
    
    # Retourne triée par taille décroissante (prêt pour l'algorithme greedy)
    return rectangles


def solve(nvars, vals):
    """
    FONCTION PRINCIPALE : Résout un tableau de Karnaugh avec un algorithme greedy.
    
    Entrées :
      nvars : string "2", "3" ou "4" (nombre de variables)
      vals : string "1,0,0,1,X,..." (valeurs séparées par virgules)
    
    Sortie : string contenant les commandes LaTeX \kvgroup[color]{indices}
             une par groupe trouvé, prêtes à être insérer dans le LaTeX
    
    ALGORITHME GREEDY (la solution du problème) :
      1. Parse les entrées et détermine la taille de la grille
      2. Identifie les '1' et 'X' (don't cares)
      3. Génère TOUS les rectangles possibles (triés par taille ↓)
      4. Parcourt les rectangles dans l'ordre décroissant
      5. Pour chaque rectangle :
         - Si couvre au moins un '1' non couvert :
           * Ajoute à la solution
           * Marque ses '1' comme couverts
         - Arrête quand tous les '1' sont couverts
      6. Génère les commandes LaTeX avec couleurs attribuées
    
    POURQUOI GREEDY ? L'approche glouton (prendre le plus grand d'abord) donne
    la majorité du temps la solution optimale pour Karnaugh, et c'est rapide.
    """
    # Parse le nombre de variables
    nvars = int(nvars)
    
    # Parse les valeurs (enlève espaces et convertit en majuscules)
    vals = [v.strip().upper() for v in vals.split(',')]

    # Détermine la taille de la grille selon nvars
    if nvars == 2:   nr, nc = 2, 2      # 2 variables = 4 cellules (2x2)
    elif nvars == 3: nr, nc = 2, 4      # 3 variables = 8 cellules (2x4)
    else:            nr, nc = 4, 4      # 4 variables = 16 cellules (4x4)

    # ÉTAPE 1 : Identifie les '1' et 'X' (don't cares) par leur indice minterm
    ones = {i for i, v in enumerate(vals) if v == '1'}      # Ensemble des '1'
    dcs  = {i for i, v in enumerate(vals) if v == 'X'}      # Ensemble des 'X'
    ones_and_dcs = ones | dcs  # Union : les cellules qu'on peut utiliser
    
    covered = set()  # Ensemble des '1' déjà couverts par des groupes
    groups = []      # Liste des groupes trouvés (ensembles de minterms)

    # ÉTAPE 2 : Génère TOUS les rectangles possibles, triés par taille ↓
    rectangles = generate_all_rectangles(nvars, nc, nr, ones_and_dcs)

    # ÉTAPE 3 : Algorithme greedy
    for size, rect, wrap_r, wrap_c in rectangles:
        # Calcule les '1' du rectangle qui ne sont pas encore couverts
        uncovered_ones = (rect & ones) - covered
        
        # Si ce rectangle couvre du nouveau terrain
        if uncovered_ones:
            # Ajoute le groupe à la solution
            groups.append((rect, wrap_r, wrap_c))
            # Marque tous les '1' du rectangle comme couverts
            covered |= (rect & ones)
        
        # Arrête dès que tous les '1' sont couverts (optimisation)
        if covered == ones:
            break

    # ÉTAPE 4 : Génère les commandes LaTeX
    # Palette de 8 couleurs TikZ (cycles si plus de 8 groupes)
    palette = ['red!60', 'blue!60', 'green!60', 'orange!70',
               'purple!60', 'teal!60', 'cyan!60', 'magenta!50']

    lines = []  # Accumule les commandes LaTeX
    counter = 0
    for rect, wrap_r, wrap_c in groups:
        # Choisit une couleur (cycle sur la palette si i >= 8)
        color = palette[counter % len(palette)]
        counter += 1
        # Convertit les minterms en string sépaés par virgules
        indices = ','.join(str(m) for m in sorted(rect))
        # Génère la commande : \kvgroup[color]{indices}
        lines.append(f'\\kvgroup{{{color}}}{{{wrap_r}}}{{{wrap_c}}}{{{indices}}}')

    # Retourne les commandes LaTeX séparées par des retours à la ligne
    return '\n'.join(lines)

if __name__ == '__main__':
    """
    POINT D'ENTRÉE : Appelé depuis LaTeX via \write18 (shell-escape).
    
    Usage (depuis LaTeX) :
      \kvautogroup  -> exécute : python3 logique_karnaugh.py 4 "1,0,0,1,X,..."
    
    Paramètres de la ligne de commande :
      sys.argv[1] : nvars (nombre de variables)
      sys.argv[2] : vals (valeurs séparées par virgules)
    
    Sortie : Imprime les commandes LaTeX \kvgroup[color]{indices} sur stdout
             qui sera capturé et inséré dans le fichier kv_tmp.tex
    """
    if len(sys.argv) > 2:
        # Appelle solve() avec les paramètres et affiche le résultat
        print(solve(sys.argv[1], sys.argv[2]))