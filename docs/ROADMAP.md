# Roadmap: Improvements and Extensions

The core assignment scope (see [SPECIFICATION.md](SPECIFICATION.md)) is
implemented. This document tracks improvements beyond it, in priority order.

Status: ✅ done · 🚧 in progress · ⬜ planned · ⏸ parked

---

## Assignment deliverables

| Item | Notes |
|---|---|
| ⏸ Report | Q2/Q3 write-up with worked instances, design decisions, errata |
| ✅ Demonstration | `demo.py`: seven-section terminal walkthrough of the textbook examples, manipulation cases, experiments and exhaustive results |
| ⏸ Figure 5.3 test | Needs the edge list read from the figure |

## Priority

| # | Item | Why |
|---|---|---|
| 1 | ✅ **Exhaustive verification of Theorem 5.4** | Random sampling cannot prove there are no Q2 counterexamples. `experiments/exhaustive.py` checks every directed graph on up to 5 arguments against every possible argument set for one agent (with disjoint types, the other agents jointly reveal any subset of the remaining arguments). This covers both readings of "odd-length path" and graphs with self-attacks. Extending to n = 6 (2³⁰ graphs) needs isomorphism reduction |
| 2 | ✅ **CI and code quality** | GitHub Actions runs pytest with coverage on Python 3.10–3.13, plus `ruff` lint and format checks and `mypy` type checking. Status badge in the README. Library coverage is 97% |
| 3 | ✅ **Graph visualisation** | `argumentation/visualize.py` renders frameworks with Graphviz, coloured by labelling (in = green, out = red, undec = grey), with before/after views of a manipulation. Figures are in `docs/figures/` |

Exhaustive verification found **zero** counterexamples to Theorem 5.4: 6.3M
(graph, agent set) pairs without self-attacks and 201.7M with them, under both
readings of "odd-length path". See the README for details.

## Engineering

| Item | Description |
|---|---|
| ⬜ Command-line interface | e.g. `argengine solve graph.apx --semantics preferred`; read and write ASPARTIX `.apx` and ICCMA `.tgf` formats |
| 🚧 Bitmask representation | Represent argument sets as integer bitmasks to speed up grounded and best-response computation; benchmark against the set-based version. A bitmask engine already exists in `experiments/exhaustive.py`; what remains is moving it into the library and benchmarking it |
| ⬜ Scalable extension search | Labelling-based backtracking or SAT encoding for large frameworks (hundreds of arguments) |
| ⬜ Property-based tests | Hypothesis-generated graphs checking invariants: stable ⊆ semi-stable ⊆ preferred ⊆ complete, grounded ⊆ every complete extension, labelling–extension bijection |
| ⬜ PyPI release | Publish the package so it installs with `pip install` |

## Research extensions

| Item | Question |
|---|---|
| ⬜ Focal-argument utilities | If each agent cares about a single focal argument rather than a count, how does strategyproofness change? |
| ⬜ Other mechanism semantics | Replace grounded with preferred or credulous acceptance and compare manipulation rates |
| ⬜ Scaling and graph models | Vary the number of agents and arguments, and the graph model (Erdős–Rényi vs scale-free), not just p |
| ⬜ Coalitional manipulation | Can groups of agents gain by jointly hiding arguments? |
