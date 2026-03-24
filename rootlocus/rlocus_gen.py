#!/usr/bin/env python3
# ============================================================
#  rlocus_gen.py  --  Generateur de donnees pour rootlocus.sty
#  Appele par LaTeX via \write18 / shell-escape
#
#  Usage :
#    python3 rlocus_gen.py  <num>  <den>  <outbase>  [npoints]
#
#  Sorties :
#    <base>.dat      Re Im par branche (blocs separes par ligne vide)
#    <base>_bN.dat   branche N separee  (pour pgfplots)
#    <base>.tex      macros LaTeX (xmin, xmax, poles, zeros, ...)
# ============================================================

import sys, os, math
import numpy as np

def parse_poly(s):
    return [float(x.strip()) for x in s.split(',')]

def compute_rootlocus(num_c, den_c, npoints=600):
    p_den   = np.poly1d(den_c)
    p_num   = np.poly1d(num_c)
    n_poles = len(den_c) - 1
    k_vals  = np.concatenate([[0.0], np.logspace(-5, 5, npoints - 1)])
    rlist   = np.zeros((npoints, n_poles), dtype=complex)
    prev    = None
    for i, k in enumerate(k_vals):
        roots = np.roots((p_den + k * p_num).coeffs)
        if prev is None:
            roots = roots[np.argsort(roots.real)[::-1]]
        else:
            ordered = np.empty_like(roots)
            avail   = list(roots)
            for j, rp in enumerate(prev):
                idx = int(np.argmin([abs(r - rp) for r in avail]))
                ordered[j] = avail.pop(idx)
            roots = ordered
        rlist[i] = roots
        prev = roots
    return k_vals, rlist

def asymptotes(poles, zeros):
    n, m = len(poles), len(zeros)
    if n <= m:
        return None, []
    sigma_a = (sum(p.real for p in poles) - sum(z.real for z in zeros)) / (n - m)
    return sigma_a, [(180 + 360*k)/(n-m) for k in range(n-m)]

def smart_ylim(poles, zeros, rlist, factor=6.0, min_lim=2.0):
    pz_im = [abs(p.imag) for p in poles] + [abs(z.imag) for z in zeros]
    base  = max(pz_im) * factor if pz_im and max(pz_im) > 0 else min_lim
    return max(base, min_lim)

def fmt(v):
    """Formate un float pour LaTeX : pas de notation scientifique."""
    return "{:.6f}".format(v)

def main():
    if len(sys.argv) < 4:
        print("Usage: rlocus_gen.py <num> <den> <outbase> [npoints]")
        sys.exit(1)

    num_c   = parse_poly(sys.argv[1])
    den_c   = parse_poly(sys.argv[2])
    outbase = sys.argv[3]
    npoints = int(sys.argv[4]) if len(sys.argv) > 4 else 600

    klist, rlist = compute_rootlocus(num_c, den_c, npoints)
    n_branches   = rlist.shape[1]

    poles_v  = np.roots(den_c)
    zeros_v  = np.roots(num_c) if len(num_c) > 1 else np.array([])
    sigma_a, angles = asymptotes(poles_v, zeros_v)
    ylim     = smart_ylim(poles_v, zeros_v, rlist)

    all_re   = list(rlist.real.flatten()) + \
               [p.real for p in poles_v] + [z.real for z in zeros_v]
    margin   = max(0.5, (max(all_re) - min(all_re)) * 0.1)
    xmin     = min(all_re) - margin
    xmax     = max(all_re) + margin

    # ── _bN.dat  (une branche par fichier) ───────────────────
    for b in range(n_branches):
        with open("{}_b{}.dat".format(outbase, b+1), 'w') as f:
            for i in range(npoints):
                re = rlist[i, b].real
                im = rlist[i, b].imag
                if abs(im) <= ylim * 1.05:
                    f.write("{} {}\n".format(fmt(re), fmt(im)))

    # ── .tex  (macros LaTeX) ─────────────────────────────────
    with open(outbase + ".tex", 'w') as f:
        f.write("%% Auto-genere par rlocus_gen.py\n")
        f.write("%% num={} den={}\n".format(sys.argv[1], sys.argv[2]))
        f.write("\\def\\RLxmin{{{}}}\n".format(fmt(xmin)))
        f.write("\\def\\RLxmax{{{}}}\n".format(fmt(xmax)))
        f.write("\\def\\RLymin{{{}}}\n".format(fmt(-ylim)))
        f.write("\\def\\RLymax{{{}}}\n".format(fmt( ylim)))
        f.write("\\def\\RLbranches{{{}}}\n".format(n_branches))

        # Poles : liste "re,im;re,im;..."
        pole_str = ",".join("{}/{}".format(fmt(p.real), fmt(p.imag))
                            for p in poles_v)
        f.write("\\def\\RLpolelist{{{}}}\n".format(pole_str))
        f.write("\\def\\RLnumpoles{{{}}}\n".format(len(poles_v)))

        # Zeros
        zero_str = ",".join("{}/{}".format(fmt(z.real), fmt(z.imag))
                            for z in zeros_v)
        f.write("\\def\\RLzerolist{{{}}}\n".format(zero_str))
        f.write("\\def\\RLnumzeros{{{}}}\n".format(len(zeros_v)))

        # Asymptotes : "sigma,angle;..."
        if sigma_a is not None:
            asym_str = ",".join("{}/{}".format(fmt(sigma_a), fmt(a))
                                for a in angles)
            f.write("\\def\\RLasymptlist{{{}}}\n".format(asym_str))
            f.write("\\def\\RLnumasympt{{{}}}\n".format(len(angles)))
            f.write("\\def\\RLcentroid{{{}}}\n".format(fmt(sigma_a)))
        else:
            f.write("\\def\\RLasymptlist{}\n")
            f.write("\\def\\RLnumasympt{0}\n")
            f.write("\\def\\RLcentroid{}\n")

    print("OK {} branches -> {}_b1.dat .. {}_b{}.dat + {}.tex".format(
          n_branches, outbase, outbase, n_branches, outbase))

if __name__ == '__main__':
    main()
