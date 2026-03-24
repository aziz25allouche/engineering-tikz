# karnaughTikz

LaTeX/TikZ package for drawing Karnaugh maps with 2, 3, or 4 variables,
including colored groupings.

## Usage

```latex
\usepackage{karnaughTikz}

% 2 variables
\begin{karnaugh}{2}{A,B}{1,0,0,1}
  \kvgroup[blue!70]{0,3}
\end{karnaugh}

% 3 variables
\begin{karnaugh}{3}{A,B,C}{1,1,0,0,0,0,1,1}
  \kvgroup[red!60]{0,1}
  \kvgroup[blue!60]{3,7}
\end{karnaugh}

% 4 variables
\begin{karnaugh}[cell=1.1cm, index=true]{4}{A,B,C,D}%
  {0,1,1,0, 1,1,0,0, 1,1,0,0, 0,1,0,0}
  \kvgroup[red!60]{0,1,4,5}
  \kvgroup[blue!60]{2,3,6,7}
  \kvgroup[green!60]{5,7,13,15}
\end{karnaugh}
```

## Arguments

| Argument | Description |
|---|---|
| `n` | Number of variables: 2, 3, or 4 |
| `A,B,...` | Variable names (comma-separated) |
| `0,1,X,...` | Cell values in **minterm order** (0 to 2^n - 1) |

Values can be `0`, `1`, or `X` (don't care).

## Commands

`\kvgroup[color]{i,j,...}` — Draw a rounded rectangle grouping
the listed minterms. Default color: `red!70`.

## Options

| Option | Default | Description |
|---|---|---|
| `cell` | `1cm` | Cell size |
| `index` | `false` | Show minterm index in each cell |

## Grid layout (Gray code)

The columns and rows follow Gray code order:

**4 variables (4×4):**
```
       CD=00  CD=01  CD=11  CD=10
AB=00 [  0 ][  1 ][  3 ][  2 ]
AB=01 [  4 ][  5 ][  7 ][  6 ]
AB=11 [ 12 ][ 13 ][ 15 ][ 14 ]
AB=10 [  8 ][  9 ][ 11 ][ 10 ]
```

## Known limitations

- Toroidal wrap-around groups (e.g. `{0,2,8,10}`) are not yet
  automatically split into two rectangles. Planned for v1.1.

## Dependencies

- TikZ
- xkeyval, xcolor, pgffor, ifthen
