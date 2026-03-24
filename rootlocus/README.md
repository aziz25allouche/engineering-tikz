# rootlocus

Automatic root locus plots from a transfer function H(s) = N(s)/D(s),
using Python (NumPy) for computation and pgfplots for rendering.

## Requirements

- `pdflatex -shell-escape`
- Python 3 + NumPy (`pip install numpy`)
- `rlocus_gen.py` in the same directory as your `.tex` file

## Usage

```latex
\usepackage{amsmath}
\usepackage{rootlocus}

% H(s) = 1 / (s^2 + 3s + 2)
\rootlocus{1}{1,3,2}

% H(s) = (s+1) / (s(s+2)(s+3))  with options
\rootlocus[width=8cm, height=7cm,
           label={$H(s)=\frac{s+1}{s(s+2)(s+3)}$}]
          {1,1}{1,5,6,0}
```

Coefficients are in **descending order**, comma-separated:
- `s^2 + 3s + 2` → `1,3,2`
- `s(s+2)(s+3) = s^3 + 5s^2 + 6s` → `1,5,6,0`

## Compilation

```bash
pdflatex -shell-escape your_document.tex
```

On first run, `rlocus_gen.py` is called automatically via `\write18`.
Generated data files (`.dat`, `.tex`) are cached — recomputation
only happens if you delete them.

## Options

| Option | Default | Description |
|---|---|---|
| `width` | `7cm` | Plot width |
| `height` | `6cm` | Plot height |
| `points` | `600` | Computation points per branch |
| `label` | (empty) | Plot title |
| `stable` | `true` | Shade Re < 0 region in green |
| `grid` | `true` | Show grid |
| `script` | `./rlocus_gen.py` | Path to Python script |
| `datadir` | `.` | Directory for generated data files |

## How it works

1. LaTeX calls `rlocus_gen.py` via `\write18`
2. Python computes the locus by sweeping K from 0 to 10^5
3. Results saved as `rl_<num>__<den>.tex` (macros) and `_b1.dat`, `_b2.dat`, ... (branch data)
4. LaTeX `\input`s the macros and pgfplots reads the `.dat` files

## Dependencies

- TikZ, pgfplots (compat=1.18)
- pgffor, xkeyval, xstring, ifthen, xcolor
