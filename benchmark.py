"""
benchmark.py
Compares plain recursive vs deterministic (memoized) for two algorithms:
  - Fibonacci   : single-argument recursion, exponential call growth
  - Knapsack    : two-argument DP, 2D subproblem reuse

Run: python benchmark.py
"""

import time
import sys

sys.setrecursionlimit(500_000)

REPEATS = 3


# ── Fibonacci ─────────────────────────────────────────────────────────────────

def fib_plain(n: int) -> int:
    if n <= 1:
        return 1
    return fib_plain(n - 1) + fib_plain(n - 2)


_fib_memo: dict = {}

def fib_det(n: int) -> int:
    if n in _fib_memo:
        return _fib_memo[n]
    if n <= 1:
        _fib_memo[n] = 1
        return 1
    _fib_memo[n] = fib_det(n - 1) + fib_det(n - 2)
    return _fib_memo[n]


# ── Knapsack ──────────────────────────────────────────────────────────────────

def knapsack_plain(weights, values, n: int, cap: int) -> int:
    if n == 0 or cap == 0:
        return 0
    if weights[n - 1] > cap:
        return knapsack_plain(weights, values, n - 1, cap)
    include = values[n - 1] + knapsack_plain(weights, values, n - 1, cap - weights[n - 1])
    exclude = knapsack_plain(weights, values, n - 1, cap)
    return max(include, exclude)


_ks_memo: dict = {}

def knapsack_det(weights, values, n: int, cap: int) -> int:
    key = (n, cap)
    if key in _ks_memo:
        return _ks_memo[key]
    if n == 0 or cap == 0:
        _ks_memo[key] = 0
        return 0
    if weights[n - 1] > cap:
        result = knapsack_det(weights, values, n - 1, cap)
    else:
        include = values[n - 1] + knapsack_det(weights, values, n - 1, cap - weights[n - 1])
        exclude = knapsack_det(weights, values, n - 1, cap)
        result = max(include, exclude)
    _ks_memo[key] = result
    return result


# ── Benchmark runner ──────────────────────────────────────────────────────────

def mean(times): return sum(times) / len(times)

def run(fn, *args) -> float:
    t0 = time.perf_counter()
    fn(*args)
    return time.perf_counter() - t0


# ── Fibonacci benchmark ───────────────────────────────────────────────────────

FIB_TESTS = [20, 30, 35]

print()
print("  ── Fibonacci ─────────────────────────────────────────────────────────")
print(f"  {'n':>4}  {'plain (s)':>12}  {'deterministic (s)':>18}  {'speedup':>10}  {'plain calls':>12}")
print("  " + "─" * 64)

for n in FIB_TESTS:
    t_plain = mean([run(fib_plain, n) for _ in range(REPEATS)])

    det_times = []
    for _ in range(REPEATS):
        _fib_memo.clear()
        det_times.append(run(fib_det, n))
    t_det = mean(det_times)

    speedup    = t_plain / t_det if t_det > 0 else float("inf")
    # plain call count ≈ 2*fib(n+1) - 1  (exact for this definition)
    _fib_memo.clear()
    fib_det(n)
    unique = len(_fib_memo)

    print(f"  {n:>4}  {t_plain:>12.6f}  {t_det:>18.8f}  {speedup:>9.0f}x  {unique:>9} unique")


# ── Knapsack benchmark ────────────────────────────────────────────────────────

import random
random.seed(42)

KS_TESTS = [
    (10, 20),
    (15, 30),
    (20, 40),
]

print()
print("  ── Knapsack (random items, increasing size) ──────────────────────────")
print(f"  {'items':>5}  {'capacity':>8}  {'plain (s)':>12}  {'deterministic (s)':>18}  {'speedup':>10}  {'unique subproblems':>18}")
print("  " + "─" * 80)

for n_items, capacity in KS_TESTS:
    weights = [random.randint(1, 10) for _ in range(n_items)]
    values  = [random.randint(1, 10) for _ in range(n_items)]

    t_plain = mean([run(knapsack_plain, weights, values, n_items, capacity)
                    for _ in range(REPEATS)])

    det_times = []
    for _ in range(REPEATS):
        _ks_memo.clear()
        det_times.append(run(knapsack_det, weights, values, n_items, capacity))
    t_det = mean(det_times)

    speedup = t_plain / t_det if t_det > 0 else float("inf")
    _ks_memo.clear()
    knapsack_det(weights, values, n_items, capacity)
    unique = len(_ks_memo)

    print(f"  {n_items:>5}  {capacity:>8}  {t_plain:>12.6f}  {t_det:>18.8f}  {speedup:>9.0f}x  {unique:>14} pairs")

print()
print("  Each result is the mean of 3 runs.")
print("  'unique' = distinct (args) tuples computed — everything else is a cache hit.")
print()
