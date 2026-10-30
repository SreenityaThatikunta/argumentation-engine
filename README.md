# Argumentation Engine

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-in%20development-orange)

A Python library for **abstract argumentation** and **strategic argumentation**.
It computes which arguments a rational agent should accept in a debate, and it
analyses whether self-interested agents can manipulate the outcome by hiding
arguments.

The project combines formal logic (Dung-style argumentation semantics) with
game theory (mechanism design and strategyproofness). It then tests a published
theorem empirically through large-scale simulations.

---

## Overview

**Reasoning engine.** Models a debate as a directed graph of arguments and
attacks. Computes the standard acceptability semantics:

- grounded
- complete
- preferred
- stable
- semi-stable

It also generates every legal in/out/undec labelling and classifies each
argument as skeptically accepted, credulously accepted, or rejected.

**Strategic analysis.** Models multiple agents that each hold private arguments
and choose what to reveal to a judge, the *grounded direct argumentation
mechanism*. The engine:

- finds each agent's best responses
- verifies strategyproofness exhaustively
- checks a graph-theoretic sufficient condition for strategyproofness, which
  requires parity-aware path search on cyclic graphs

**Experiments.** Generates thousands of random multi-agent instances and
measures how often truthful revelation is optimal. It also identifies the
cases where the theoretical condition and actual behaviour disagree.

## Getting Started

```bash
git clone https://github.com/SreenityaThatikunta/argumentation-engine.git
cd argumentation-engine
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

```python
from argumentation import (
    ArgumentationFramework, acceptance_status, grounded,
    legal_labellings, preferred_extensions,
)

# a1 and a2 attack each other; a3 is unattacked
af = ArgumentationFramework(["a1", "a2", "a3"], [("a1", "a2"), ("a2", "a1")])

af.is_conflict_free({"a1", "a3"})   # True
af.characteristic({"a3"})           # F(S) = {a3}
grounded(af)                        # {a3}
preferred_extensions(af)            # [{a1, a3}, {a2, a3}]
legal_labellings(af)                # 3 in/out/undec labellings
acceptance_status(af, "a1")         # credulously accepted (preferred semantics)
```

## Roadmap

- [x] Argumentation framework: conflict-freeness, defence, characteristic function
- [x] Admissible and complete set checks
- [x] Grounded, complete, preferred, stable and semi-stable extensions
- [x] Labelling enumeration and argument acceptance status
- [ ] Grounded direct argumentation mechanism and best-response search
- [ ] Strategyproofness verification (Theorem 5.3) and graph condition (Theorem 5.4)
- [ ] Randomised experiments with results and plots
- [ ] Test suite built from textbook examples
- [ ] Report and demo walkthrough

## Documentation

- [Project specification](docs/SPECIFICATION.md): full scope, definitions,
  validation cases, experiment design, and known textbook errata

## Reference

I. Rahwan, "Argumentation among Agents," Chapter 5 in G. Weiss (ed.),
*Multiagent Systems*, 2nd ed., MIT Press, 2013.

## License

Released under the [MIT License](LICENSE).
