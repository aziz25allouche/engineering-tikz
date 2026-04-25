# logiTikz - Logic Circuit Diagram Generation v2.0

LaTeX/TikZ package for drawing logic gate diagrams with **automatic expression parsing** and **optimized layout**.

## Features

✓ **Automatic Expression Parsing** - Input logic equations directly  
✓ **Operator Precedence** - Correctly handles parentheses, NOT, AND, OR, XOR  
✓ **Vertical Input Lines** - Clean input organization with circular node markers  
✓ **Optimized Gate Placement** - Hierarchical layout based on expression depth  
✓ **Multiple Operator Syntax** - Flexible notation (~, !, &, ., |, +, ^)

## Quick Start

### New Automatic Parsing (v2.0+)

```latex
\documentclass{article}
\usepackage{logiTikz}

\begin{document}

% Simple expressions with automatic parsing
\logicgraph{A & B}                    % AND gate
\logicgraph{A | B}                    % OR gate
\logicgraph{~A}                       % NOT gate
\logicgraph{(A & B) | ~C}            % Complex expression
\logicgraph{(A ^ B) & (C | D)}       % XOR + OR + AND

% With customization
\logicgraph[unit=1.5cm]{(A & B) | ~C}
\logicgraph[scale=1.2]{A & B & C & D}

\end{document}
```

### Legacy Manual Syntax (v1.0)

```latex
\begin{logigramme}[style=american]{$S$}
  \INPUT{$A$}
  \INPUT{$B$}
  \INPUT{$C$}
  \GATE{g1}{and}{i1}{i2}
  \UGATE{g2}{not}{i3}
  \GATE{g3}{or}{g1}{g2}
  \OUT{g3}
\end{logigramme}
```

## Supported Operators (Precedence Order)

| Precedence | Operator | Syntax | Alternative |
|:-:|---|---|---|
| 1 | Parentheses | `()` | - |
| 2 | NOT | `~A` | `!A` |
| 3 | AND | `A & B` | `A . B` |
| 4 | OR | `A \| B` | `A + B` |
| 5 | XOR | `A ^ B` | - |

## Circuit Design Architecture

### Input Placement with Vertical Line

All inputs appear as circular nodes connected to a vertical backbone:

```
Input Variables (Vertical Line)
┌────── A ●────┐
├────── B ●    ├─→ Gate Layer 1 (NOT, atomic ops)
│              │─→ Gate Layer 2 (AND operations)  
├────── C ●    ├─→ Gate Layer 3 (OR operations)
│              │
└────── D ●────┴─→ Output

Features:
• Clean organization
• Easy input identification  
• Minimized connection crossings
• Scalable for many variables
```

### Gate Placement Algorithm

1. **Extract Variables** - Identify unique inputs
2. **Parse Expression** - Build abstract syntax tree respecting precedence
3. **Compute Depth** - Determine computation level for each gate
4. **Position Gates** - Arrange hierarchically (left to right)
5. **Optimize Layout** - Minimize wire crossings
6. **Render Circuit** - Draw TikZ components

### Expression Examples

#### Basic Gates
```latex
\logicgraph{A & B}              → AND gate with inputs A, B
\logicgraph{A | B}              → OR gate with inputs A, B
\logicgraph{~A}                 → NOT gate with input A
```

#### Compound Expressions  
```latex
\logicgraph{~(A & B)}           → NAND equivalent
\logicgraph{~(A | B)}           → NOR equivalent
\logicgraph{(A ^ B) ^ C}        → 3-input XOR
\logicgraph{A & B | C & D}      → (A·B) + (C·D)
```

#### Complex Circuits
```latex
% Full adder sum: A XOR B XOR C_in
\logicgraph{A ^ B ^ C}

% Full adder carry: (A & B) | (B & C) | (C & A)  
\logicgraph{(A & B) | (B & C) | (C & A)}

% Multiplexer: (A & ~S) | (B & S)
\logicgraph{(A & ~S) | (B & S)}
```

## Customization Options

```latex
% Set unit distance between components (default: 1.2cm)
\logicgraph[unit=2cm]{A & B | C}

% Scale entire diagram (default: 1.0)
\logicgraph[scale=1.5]{(A & B) | ~C}

% Adjust spacing (default: 0.5)
\logicgraph[spacing=0.8]{A ^ B ^ C}
```

## Gate Types

### Standard Gates
- **AND** (`&`, `.`) - All inputs high
- **OR** (`|`, `+`) - Any input high  
- **NOT** (`~`, `!`) - Invert input
- **XOR** (`^`) - Odd number of highs

### Derived Gates (via expressions)
- **NAND** - `~(A & B)`
- **NOR** - `~(A | B)`
- **XNOR** - `~(A ^ B)`

## Color Scheme

| Element | Color | RGB |
|---|---|---|
| Input Nodes | Light Blue | (210,230,255) |
| Logic Gates | Light Blue | (225,232,248) |
| NOT Gates | Light Orange | (248,235,215) |
| Output Node | Green | (230,245,210) |
| Wire Lines | Dark Gray | (35,35,35) |

## Performance

- **Variables**: Supports 2-26+ inputs (A-Z)
- **Expression Depth**: Handles complex nested structures
- **Rendering**: Real-time LaTeX compilation
- **Memory**: Minimal overhead for expression macros

## Dependencies

- TikZ (required)
- xkeyval (key-value options)
- xstring (string manipulation)
- ifthen (conditionals)
- etoolbox (programming tools)
- xcolor (colors)

## Algorithm Details

### Recursive Descent Parser
The package uses a stack-based parser to handle:
- Operator precedence (NOT > AND > OR > XOR)
- Parenthesized sub-expressions
- Input variable extraction
- Gate dependency tracking

### Hierarchical Layout
```
Level 0: Input variables (vertical line)
Level 1: NOT gates (highest precedence)
Level 2: AND gates (binary combinations)
Level 3: OR gates (combining levels)
Level N: Final output
```

### Connection Optimization
- Vertical lines from inputs to gates
- Horizontal lines between gate levels
- Minimal edge crossing via topological sort

## Mathematical Representation

For expression: $f = (A \land B) \lor (\neg C \land D)$

```
\logicgraph{(A & B) | (~C & D)}
```

Computation:
1. $t_1 = A \land B$ (AND gate $g_1$)
2. $t_2 = \neg C$ (NOT gate $g_2$)
3. $t_3 = t_2 \land D$ (AND gate $g_3$)
4. $f = t_1 \lor t_3$ (OR gate $g_4$)

## Troubleshooting

| Problem | Solution |
|---|---|
| Gates overlap | Increase `unit` parameter |
| Diagram too small | Increase `scale` parameter |
| Expression errors | Check parentheses and operator syntax |
| Slow compilation | Reduce expression complexity |

## Version History

- **v2.0** (2026-04-01) - Automatic expression parsing, optimized layout
- **v1.0** (2026-03-01) - Manual gate construction syntax

## License

Engineering Package Collection (2026)

---

**For questions or bug reports**, refer to package documentation and source comments.
