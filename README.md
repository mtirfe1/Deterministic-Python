# Deterministic Python

> An experimental Python extension that introduces `deterministic` functions —  
> automatically memoized and built on real AST transformation.

```
python3 deterministic fib.dpy
```

```
[det] Found 1 deterministic function(s): fib

fib(0) → computing
fib(1) → computing
fib(2) → computing
fib(1) → cache hit
fib(0) → cache hit
fib(3) → computing
fib(2) → cache hit
...

┌─ cache stats ───────────────┐
│  fib  ██████████  10 entries │
└─────────────────────────────┘
```

---

## What is this?

Deterministic Python is a mini-language extension for Python that adds a single new keyword: `deterministic`.

Mark a function `deterministic` and the interpreter guarantees:

- **Automatic memoization** — identical inputs always return the cached result.
- **Call graph analysis** — the interpreter statically detects which deterministic functions call each other, derived directly from the AST.
- **Impurity warnings** — warns at load time if a `deterministic` function calls something known to be impure (`random()`, `time()`, file I/O, etc.).
- **Cache visualization** — `cache_stats()` gives a live view of every function's cache at any point during execution.

This project is an exploration of **recursion optimization**, **AST transformation**, and **language design** — the same ideas that underpin tools like `dataclasses`, type checkers, and optimizing compilers.

---

## How it works

The interpreter runs a 6-step pipeline on every `.dpy` file:

```
.dpy source
  ↓  keyword extraction        — finds `deterministic` declarations, replaces with `def`
  ↓  ast.parse()               — produces a full syntax tree
  ↓  DeterministicTransformer  — NodeTransformer: injects @_make_deterministic,
  ↓                               builds call graph, runs impurity checks
  ↓  ast.fix_missing_locations()
  ↓  compile()                 — byte-compiles the merged AST
  ↓  exec()                    — runs in an isolated namespace
```

There is no regex substitution at execution time. The `deterministic` keyword is stripped in a pre-pass so the source becomes valid Python, then the **entire transformation happens on the AST** via `ast.NodeTransformer`. The decorator `@_make_deterministic` is injected directly into `node.decorator_list` — not the source string.

---

## Installation

```bash
git clone 
cd deterministic-python
```

Requires Python 3.9+. No dependencies.

---

## Usage

```bash
python3 deterministic <file.dpy> [options]
```

| Flag | Description |
|---|---|
| `--show-source` | Print the transformed Python source before running |
| `--show-ast` | Print the full AST dump before running |
| `--show-graph` | Print the deterministic call graph before running |

---

## Examples

### Fibonacci

```python
# fib.dpy

deterministic fib(n):
    if n <= 1:
        return 1
    return fib(n - 1) + fib(n - 2)

for i in range(10):
    fib(i)

cache_stats()
```

```
fib(0) → computing
fib(1) → computing
fib(2) → computing
fib(1) → cache hit       ← subproblem reused immediately
fib(0) → cache hit
fib(3) → computing
fib(2) → cache hit
...

┌─ cache stats ───────────────┐
│  fib  ██████████  10 entries │
└─────────────────────────────┘
```

Without memoization, `fib(35)` calls itself **29 million** times.  
With `deterministic`, it makes exactly **36 unique calls**.

---

### Knapsack (2D dynamic programming)

```python
# knapsack.dpy

weights  = [2, 3, 4, 5]
values   = [3, 4, 5, 6]
capacity = 8

deterministic knapsack(n, cap):
    if n == 0 or cap == 0:
        return 0
    if weights[n - 1] > cap:
        return knapsack(n - 1, cap)
    include = values[n - 1] + knapsack(n - 1, cap - weights[n - 1])
    exclude = knapsack(n - 1, cap)
    return max(include, exclude)

result = knapsack(len(weights), capacity)
print(f"Max value: {result}")
cache_stats()
```

```
knapsack(4, 8) → computing
knapsack(3, 3) → computing
...
knapsack(0, 1) → cache hit   ← subproblems reused across branches
knapsack(0, 3) → cache hit

Max value: 10

┌─ cache stats ────────────────────┐
│  knapsack  ███████████████████  19 entries │
└──────────────────────────────────┘
```

---

### Impurity warning

```python
# bad.dpy
import random

deterministic roll(sides):
    return random.randint(1, sides)   # ← not pure!
```

```
[warn] Impurity warnings:
  ⚠  line 4: `randint()` may be impure — results in `roll` could be incorrectly cached
```

The program still runs — the warning is advisory, not a hard error.

---

## Benchmarks

Run: `python3 benchmark.py`

### Fibonacci

| n | Plain | Deterministic | Speedup | Unique calls |
|---|---|---|---|---|
| 20 | 0.000547s | 0.0000033s | ~165× | 21 |
| 30 | 0.069128s | 0.0000068s | ~10,100× | 31 |
| 35 | 0.778607s | 0.0000058s | ~134,000× | 36 |

The speedup is superlinear: plain fib's call count grows as O(φⁿ) while the memoized version makes exactly O(n) unique calls.

### Knapsack

| Items | Capacity | Plain | Deterministic | Speedup | Unique subproblems |
|---|---|---|---|---|---|
| 10 | 20 | 0.000107s | 0.0000419s | ~3× | 142 pairs |
| 15 | 30 | 0.001355s | 0.000111s | ~12× | 347 pairs |
| 20 | 40 | 0.051110s | 0.000177s | ~289× | 630 pairs |

Knapsack's speedup scales differently from fib — the cache key is a `(n, cap)` tuple (2D), so unique subproblem growth is bounded by `n × capacity` rather than exponential. The speedup still compounds quickly as problem size increases.

---

## Runtime API

These functions are available in every `.dpy` file automatically:

| Function | Description |
|---|---|
| `cache_stats()` | Print a visual summary of every deterministic function's cache |

---

## Limitations

`deterministic` functions must be **pure** — given the same arguments, they must always return the same result. Avoid:

```python
deterministic bad_example(n):
    return random.random() * n     # ← different result every call
    return time.time()             # ← changes between calls
    return open("file.txt").read() # ← depends on external state
```

The interpreter will warn you about known impure calls, but it cannot catch everything. Purity is ultimately the programmer's responsibility.

---

## Project structure

```
deterministic-python/
│
├── deterministic          # interpreter (single file, no dependencies)
├── fib.dpy                # Fibonacci with cache stats
├── knapsack.dpy           # 0/1 knapsack DP
├── benchmark.py           # fib + knapsack: plain vs deterministic
├── README.md
└── LICENSE
```

---

## Why I built this

This project explores three ideas I wanted to understand deeply:

1. **AST transformation** — how Python's `ast` module lets you reshape code before it runs, the same technique used by tools like `dataclasses`, `attrs`, and type checkers.
2. **Memoization at the language level** — rather than reaching for `@lru_cache`, what if the language itself could guarantee purity and handle caching transparently?
3. **Recursion optimization** — seeing concretely how subproblem reuse collapses exponential call trees into linear ones, across both 1D and 2D DP problems.

It's a research-style CS project built for learning and portfolio purposes.

---

## License

MIT
