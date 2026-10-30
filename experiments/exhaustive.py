"""Exhaustive verification of Theorem 5.4 on every small argument graph.

Random sampling can miss rare counterexamples. This script checks every
directed graph on n arguments together with every choice of one agent's
argument set S, and asks:

* Q2: does S satisfy the Theorem 5.4 condition, yet the agent can gain by
  hiding arguments?
* Q3: is truth-telling dominant for S although the condition fails?

Reduction to a single agent: with disjoint agent types, the reports of the
other agents can jointly reveal *any* subset of A \\ S, and nothing else
matters to the agent. So strategyproofness for one agent depends only on
the graph and S, and the mechanism is strategyproof iff it is for every
agent. A counterexample found here is a counterexample to the per-agent
claim that underlies Theorem 5.4.

By relabelling arguments, S can always be taken as {0, ..., k-1}, so each
graph is checked for k = 0..n only.

Sets are bitmasks over arguments 0..n-1 for speed; ``tests/test_exhaustive.py``
cross-checks this engine against the main library.

Usage:
    python experiments/exhaustive.py --max-n 5 --out results/exhaustive
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from dataclasses import dataclass, field
from multiprocessing import Pool
from pathlib import Path

COUNTEREXAMPLE_LIMIT = 10


def edge_list(n: int, self_attacks: bool) -> list[tuple[int, int]]:
    return [(a, b) for a in range(n) for b in range(n) if self_attacks or a != b]


def decode(n: int, edges: list[tuple[int, int]], graph: int) -> tuple[list[int], list[int]]:
    """Attacker and successor bitmasks for the graph numbered ``graph``."""
    attackers = [0] * n
    successors = [0] * n
    for bit, (a, b) in enumerate(edges):
        if graph >> bit & 1:
            attackers[b] |= 1 << a
            successors[a] |= 1 << b
    return attackers, successors


def grounded(attackers: list[int], revealed: int) -> int:
    """Grounded extension of the subgraph induced by ``revealed``.

    Labels an argument ``in`` once all its revealed attackers are ``out``, and
    ``out`` once some attacker is ``in``, until nothing changes.
    """
    labelled_in = labelled_out = 0
    changed = True
    while changed:
        changed = False
        pending = revealed & ~(labelled_in | labelled_out)
        while pending:
            low = pending & -pending
            pending ^= low
            v = low.bit_length() - 1
            att = attackers[v] & revealed
            if att & ~labelled_out == 0:
                labelled_in |= low
                changed = True
            elif att & labelled_in:
                labelled_out |= low
                changed = True
    return labelled_in


def odd_walk_reach(successors: list[int], source: int) -> int:
    """Arguments reachable from ``source`` by a walk of odd length."""
    even, odd = 1 << source, 0
    while True:
        new_odd = odd | _step(successors, even)
        new_even = even | _step(successors, odd)
        if new_odd == odd and new_even == even:
            return odd
        even, odd = new_even, new_odd


def odd_simple_reach(successors: list[int], source: int) -> int:
    """Arguments reachable from ``source`` by an odd simple path (or odd cycle back)."""
    found = 0
    stack = [(source, 1 << source, 0)]
    while stack:
        node, visited, length = stack.pop()
        succ = successors[node]
        odd = (length + 1) % 2 == 1
        if odd and succ >> source & 1:
            found |= 1 << source
        nxt = succ & ~visited
        if odd:
            found |= nxt
        while nxt:
            low = nxt & -nxt
            nxt ^= low
            stack.append((low.bit_length() - 1, visited | low, length + 1))
    return found


def _step(successors: list[int], mask: int) -> int:
    out = 0
    while mask:
        low = mask & -mask
        mask ^= low
        out |= successors[low.bit_length() - 1]
    return out


def condition_holds(successors: list[int], own: int, reach) -> bool:
    """No α, β ∈ own (α = β allowed) with α ↪ β."""
    m = own
    while m:
        low = m & -m
        m ^= low
        if reach(successors, low.bit_length() - 1) & own:
            return False
    return True


def submasks(mask: int):
    sub = mask
    while True:
        yield sub
        if sub == 0:
            return
        sub = (sub - 1) & mask


def manipulation(outcomes: list[int], own: int, full: int):
    """A (others' reveal, own report) pair beating truth-telling, or None."""
    rest = full & ~own
    for others in submasks(rest):
        truthful = (outcomes[own | others] & own).bit_count()
        for report in submasks(own):
            if (outcomes[report | others] & own).bit_count() > truthful:
                return others, report
    return None


@dataclass
class Tally:
    n: int
    k: int
    pairs: int = 0
    strategyproof: int = 0
    cond_walk: int = 0
    cond_simple: int = 0
    q2_walk: int = 0
    q2_simple: int = 0
    q3_walk: int = 0
    q3_simple: int = 0
    counterexamples: list[dict] = field(default_factory=list)

    def merge(self, other: Tally) -> None:
        for name in (
            "pairs",
            "strategyproof",
            "cond_walk",
            "cond_simple",
            "q2_walk",
            "q2_simple",
            "q3_walk",
            "q3_simple",
        ):
            setattr(self, name, getattr(self, name) + getattr(other, name))
        room = COUNTEREXAMPLE_LIMIT - len(self.counterexamples)
        self.counterexamples.extend(other.counterexamples[:room])


def check_range(job: tuple[int, bool, int, int]) -> dict[int, Tally]:
    """Check graphs numbered [start, stop) on n arguments, for every k."""
    n, self_attacks, start, stop = job
    edges = edge_list(n, self_attacks)
    full = (1 << n) - 1
    tallies = {k: Tally(n, k) for k in range(n + 1)}
    for graph in range(start, stop):
        attackers, successors = decode(n, edges, graph)
        outcomes = [grounded(attackers, revealed) for revealed in range(full + 1)]
        for k in range(n + 1):
            own = (1 << k) - 1
            t = tallies[k]
            t.pairs += 1
            witness = manipulation(outcomes, own, full)
            sp = witness is None
            walk = condition_holds(successors, own, odd_walk_reach)
            simple = walk or condition_holds(successors, own, odd_simple_reach)
            t.strategyproof += sp
            t.cond_walk += walk
            t.cond_simple += simple
            t.q2_walk += walk and not sp
            t.q2_simple += simple and not sp
            t.q3_walk += sp and not walk
            t.q3_simple += sp and not simple
            if simple and not sp and len(t.counterexamples) < COUNTEREXAMPLE_LIMIT:
                others, report = witness
                t.counterexamples.append(
                    {
                        "n": n,
                        "attacks": [list(e) for i, e in enumerate(edges) if graph >> i & 1],
                        "own": _members(own),
                        "walk_condition": walk,
                        "others_reveal": _members(others),
                        "better_report": _members(report),
                        "truthful_outcome": _members(outcomes[own | others]),
                        "manipulated_outcome": _members(outcomes[report | others]),
                    }
                )
    return tallies


def _members(mask: int) -> list[int]:
    return [i for i in range(mask.bit_length()) if mask >> i & 1]


def run(n: int, self_attacks: bool, workers: int) -> dict[int, Tally]:
    graphs = 1 << len(edge_list(n, self_attacks))
    chunk = max(1, graphs // (workers * 16))
    jobs = [(n, self_attacks, s, min(s + chunk, graphs)) for s in range(0, graphs, chunk)]
    totals = {k: Tally(n, k) for k in range(n + 1)}
    with Pool(workers) as pool:
        for part in pool.imap_unordered(check_range, jobs):
            for k, tally in part.items():
                totals[k].merge(tally)
    return totals


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--max-n", type=int, default=5)
    parser.add_argument("--self-attacks", action="store_true")
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--out", type=Path, default=Path("results/exhaustive"))
    opts = parser.parse_args()

    workers = opts.workers or __import__("os").cpu_count() or 1
    rows, counterexamples = [], []
    for n in range(1, opts.max_n + 1):
        start = time.perf_counter()
        totals = run(n, opts.self_attacks, workers)
        for t in totals.values():
            row = {k: v for k, v in vars(t).items() if k != "counterexamples"}
            rows.append(row)
            counterexamples.extend(t.counterexamples)
        graphs = 1 << len(edge_list(n, opts.self_attacks))
        q2w = sum(t.q2_walk for t in totals.values())
        q2s = sum(t.q2_simple for t in totals.values())
        print(
            f"n={n}: {graphs} graphs, Q2 walk={q2w}, Q2 simple={q2s} "
            f"({time.perf_counter() - start:.1f}s)"
        )

    opts.out.mkdir(parents=True, exist_ok=True)
    with (opts.out / "summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (opts.out / "counterexamples.json").write_text(json.dumps(counterexamples, indent=1) + "\n")
    config = {"max_n": opts.max_n, "self_attacks": opts.self_attacks}
    (opts.out / "config.json").write_text(json.dumps(config, indent=2) + "\n")


if __name__ == "__main__":
    main()
