# Engineering TikZ Packages

A collection of LaTeX/TikZ packages for engineering diagrams, built for **pdfLaTeX**.

## Packages

### `logiTikz` — Logic gate diagrams

Generates logic gate diagrams (logigrammes) from a structured description.
Supports American (ANSI/IEEE) and European (IEC 60617) styles.

**Gates:** AND, OR, NOT, BUF, NAND, NOR, XOR, XNOR

```latex
\usepackage{logiTikz}

\begin{logigramme}[style=american]{$S$}
  \INPUT{$A$}  \INPUT{$B$}  \INPUT{$C$}
  \GATE{g1}{and}{i1}{i2}
  \UGATE{g2}{not}{i3}
  \GATE{g3}{or}{g1}{g2}
  \OUT{g3}
\end{logigramme}
```

**Options:** `style=american|european`, `unit=<dim>`

---

### `rootlocus` — Root locus plots (Evans)

Automatically computes and plots the root locus of a transfer function
H(s) = N(s)/D(s) using Python + pgfplots.

**Requirements:** `pdflatex -shell-escape` + Python 3 + NumPy

```latex
\usepackage{amsmath}
\usepackage{rootlocus}

% H(s) = (s+1) / (s(s+2)(s+3))
\rootlocus[width=8cm, label={$H(s)=\frac{s+1}{s(s+2)(s+3)}$}]
          {1,1}{1,5,6,0}
```

**Options:** `width`, `height`, `points`, `label`, `stable`, `grid`

Compilation:
```bash
pdflatex -shell-escape your_doc.tex
```

---

### `karnaughTikz` — Karnaugh maps

Draws Karnaugh maps for 2, 3, or 4 variables with colored groupings.

```latex
\usepackage{karnaughTikz}

\begin{karnaugh}[cell=1.1cm]{4}{A,B,C,D}%
  {0,1,1,0, 1,1,0,0, 1,1,0,0, 0,1,0,0}
  \kvgroup[red!60]{0,1,4,5}
  \kvgroup[blue!60]{2,3,6,7}
\end{karnaugh}
```

**Options:** `cell=<dim>`, `index=true|false`

---

## In progress

- `masonTikz` — Mason signal flow graphs (pdfLaTeX native)
- `stepresponse` — Annotated step response plots
- Grafcet / SFC diagrams
- P&ID diagrams

## Requirements

All packages require:
- pdfLaTeX (TeX Live 2020+)
- TikZ / PGF
- `pgfplots` (for `rootlocus`)
- Python 3 + NumPy (for `rootlocus` only)

## License

MIT
