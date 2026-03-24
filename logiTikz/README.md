# logiTikz

LaTeX/TikZ package for drawing logic gate diagrams (logigrammes).

## Usage

```latex
\usepackage{logiTikz}

\begin{logigramme}[style=american]{$S$}
  \INPUT{$A$}
  \INPUT{$B$}
  \INPUT{$C$}
  \GATE{g1}{and}{i1}{i2}    % AND gate: inputs A, B
  \UGATE{g2}{not}{i3}       % NOT gate: input C
  \GATE{g3}{or}{g1}{g2}     % OR gate: g1, g2
  \OUT{g3}
\end{logigramme}
```

## Commands

| Command | Description |
|---|---|
| `\INPUT{name}` | Declare a primary input. Auto-assigned id: `i1`, `i2`, ... |
| `\GATE{id}{type}{in1}{in2}` | Binary gate |
| `\UGATE{id}{type}{in1}` | Unary gate (NOT, BUF) |
| `\OUT{id}` | Declare the output gate |

## Gate types

`and` `or` `not` `buf` `nand` `nor` `xor` `xnor`

## Options

| Option | Values | Default |
|---|---|---|
| `style` | `american`, `european` | `american` |
| `unit` | any dimension | `1.7cm` |

## Algorithm

Gate placement is computed automatically:
- **Column** = depth in the circuit tree (topological sort, N passes)
- **Row** = average of input rows

## Dependencies

- TikZ
- xkeyval, xstring, ifthen, etoolbox, xcolor, pgffor
