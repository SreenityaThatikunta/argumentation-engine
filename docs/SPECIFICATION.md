# Project Specification

This document defines the scope of the Argumentation Engine: the reasoning
library, the strategic-argumentation (mechanism design) module, the
experiments, and the deliverables.

All definitions follow **Chapter 5, "Argumentation among Agents" (Iyad Rahwan)**
in *Multiagent Systems*, 2nd edition, edited by Gerhard Weiss (MIT Press, 2013).
Definition, theorem and example numbers below refer to that chapter.

**Status:** Parts 1 and 2 and the experiments are implemented and tested. The
demonstration is in `demo.py`; the report is pending. Arguments are named `"a1"`, `"a2"`, …
in code for the book's α1, α2, ….

---

## 1. Background

An **argumentation framework** ⟨A, ⇀⟩ is a directed graph. Nodes are arguments,
and an edge `a ⇀ b` means *a attacks b*. A **semantics** is a rule for deciding
which sets of arguments a rational reasoner can accept together. Such a set is
called an *extension*.

Notation used throughout:

- `S⁺`: the arguments attacked by some member of S
- `α⁻`: the attackers of α

---

## 2. Part 1: Argumentation Engine

A library that takes an argument graph and answers *"which arguments are
acceptable?"* Items 1–5 are methods of `ArgumentationFramework`; items 6A–6E
are functions that take a framework `af`.

| # | Component | Input → Output | Book | Code |
|---|---|---|---|---|
| 1 | `ArgumentationFramework(arguments, attacks)` | arguments + attack pairs → immutable framework object | Def 5.1 | `framework.py` |
| 2 | `af.is_conflict_free(S)` | set S → bool. No member of S attacks another member | Def 5.2 | `framework.py` |
| 3 | `af.defends(S, a)` | set S, argument a → bool. Every attacker of a is attacked by S (α⁻ ⊆ S⁺) | Def 5.2 | `framework.py` |
| 4 | `af.characteristic(S)`, written F(S) | set S → the set of all arguments S defends | Def 5.3 | `framework.py` |
| 5 | `af.is_admissible(S)`, `af.is_complete(S)` | set S → bool. Admissible: conflict-free and S ⊆ F(S). Complete: conflict-free and S = F(S) | Def 5.4, 5.5 | `framework.py` |
| 6A | `grounded(af)` | iterate F from ∅ until a fixed point → one set (the least complete extension) | Def 5.7 | `semantics.py` |
| 6B | `complete_extensions(af)` | → every conflict-free S with S = F(S) | Def 5.5 | `semantics.py` |
| 6C | `preferred_extensions(af)`, `stable_extensions(af)`, `semi_stable_extensions(af)` | **Preferred:** ⊆-maximal complete extensions. **Stable:** S⁺ = A \ S. **Semi-stable:** complete extensions with ⊆-maximal S ∪ S⁺ | Def 5.7 | `semantics.py` |
| 6D | `legal_labellings(af)` | → every legal labelling. An argument is `in` iff all its attackers are `out`, `out` iff some attacker is `in`, and `undec` otherwise. Labellings correspond one-to-one with complete extensions | Def 5.6, Table 5.1 | `labelling.py` |
| 6E | `acceptance_status(af, a, semantics="preferred")` | argument → **skeptically accepted** (in every extension), **credulously accepted** (in at least one), or **rejected** (in none) | Def 5.8 | `acceptance.py` |

**Design decision (6E):** when a semantics yields no extensions (possible for
stable), Def 5.8 read literally makes an argument skeptically accepted but not
credulously accepted. The implementation returns **rejected** in that case.

### Validation against the textbook

| Source | Graph | Expected results |
|---|---|---|
| Figure 5.1, Examples 5.5, 5.6, 5.8 | α2 ⇀ α1, α4 ⇀ α1, α3 ⇀ α2, α5 ⇀ α4 | {α1, α3, α5} is admissible. {α3, α5} is admissible but not complete. F({α3}) = {α3, α5}. Grounded is reached via F¹(∅) = {α3, α5}, F²(∅) = {α1, α3, α5}. This set is the only complete and the only preferred extension |
| Figure 5.2, Examples 5.7, 5.8 | α1 ⇄ α2, α3 unattacked | Complete extensions are {α3}, {α1, α3} and {α2, α3}. Grounded is {α3}. Preferred extensions are {α1, α3} and {α2, α3} |
| Figure 5.3 | arguments a–e (edges taken from the figure) | Grounded is {a, c, e}. **Not yet tested:** the edges appear only in the figure image |

Beyond the textbook examples, extensions and labellings are cross-checked
against brute-force enumeration (all 2ⁿ subsets, all 3ⁿ labellings) on random
graphs.

---

## 3. Part 2: Strategic Argumentation

### Setting (Defs 5.17–5.22)

Each agent *i* privately holds a set of arguments Aᵢ, called its *type*. Every
agent reports a subset of Aᵢ: it may **hide** arguments but never invent them.
The **grounded direct argumentation mechanism** builds the graph induced by
the union of all reports and outputs its grounded extension.

An agent's utility is the number of its *own* arguments that are accepted:

```
uᵢ(o) = |o ∩ Aᵢ|
```

The central question is whether an agent can ever gain by hiding arguments.
It can. Revealing one of its own arguments can break the defence of another
of its arguments, which is *indirect self-defeat*.

### Components

All components live in `argumentation/strategic.py`. `types` and `reports`
map each agent to a set of arguments. The `Game(attacks, types)` class offers
the same operations as methods and caches grounded extensions by the set of
revealed arguments.

| # | Component | Description | Book |
|---|---|---|---|
| 1 | `mechanism(attacks, reports)` | Takes the global attack relation and one revealed set per agent. Returns the grounded extension of the graph induced by the union of the reports | Def 5.21 |
| 2 | `best_responses(attacks, types, agent, others)` | Fixes the other agents' reports, enumerates all 2^\|Aᵢ\| subsets the agent could reveal, and returns the maximum utility and every report achieving it | Def 5.22 |
| 3 | `is_strategyproof(attacks, types)` | **Theorem 5.3, the exact test.** For every agent and every combination of subsets the other agents could reveal, revealing all of Aᵢ (truthfulness) must be a best response. `Game.manipulations()` lists every counterexample (agent, others' reports, better report, hidden arguments, utilities) | Thm 5.3 |
| 4 | `satisfies_theorem_5_4(attacks, types, paths="walk")` | **Theorem 5.4, the sufficient graph condition.** No agent holds two arguments α, β with an odd-length directed path from α to β in the full graph. `theorem_5_4_violations` lists the offending (agent, α, β) triples | Thm 5.4 |

### Handling cycles in Theorem 5.4

"Odd-length path" is ambiguous when the graph contains cycles:

- **Walks (`paths="walk"`, the default; vertices may repeat).** Search over
  states `(node, parity)`, so each state is visited once and cycles cannot
  cause infinite loops. Going around an odd cycle flips the parity, so the
  same pair can have both odd and even connections.
- **Simple paths (`paths="simple"`; no repeated vertices).** Enumerates paths.
  This is exponential but fast for graphs of 6–8 arguments.

Every simple path is a walk, so the walk condition is the stricter of the two.
Both readings are implemented, tested on a graph where they differ, and
compared in the experiments.

**Design decision (α = β):** pairs with α = β count as violations, matching
the theorem's formal statement ∄ α1, α2 ∈ Aᵢ with α1 ↪ α2. A self-attack is
the length-1 case, so this also enforces the theorem's requirement that each
type be conflict-free. An odd cycle back to the same argument also counts.

### Validation against the textbook

| Example | Setup | Expected result |
|---|---|---|
| **5.10** | A_x = {α1, α4, α5}, A_y = {α2}, A_z = {α3}. Attacks: α1⇀α2, α2⇀α3, α3⇀α4, α3⇀α5 | With full revelation the outcome is {α1, α3}, so u_x = 1, u_y = 0, u_z = 1. If x hides α1, the outcome is {α2, α4, α5} and u_x = 2. The mechanism is **not strategyproof**, and the Thm 5.4 condition fails |
| **5.11** | Example 5.10 plus α6 ∈ A_x with α6⇀α3 | Full revelation gives {α1, α4, α5, α6}. The mechanism is **strategyproof** even though the Thm 5.4 condition fails (α1 ↪ α4, α1 ↪ α5) |

### Known textbook errata

1. **Example 5.10:** the utilities of agents y and z are written with each
   other's argument sets. The correct values are u_y(o, {α2}) = 0 and
   u_z(o, {α3}) = 1.
2. **Discussion after Example 5.11:** the argument that cancels the indirect
   self-defeat is **α6** (it attacks α3), not α5.

---

## 4. Experiments

### Instance generation

- 3 agents
- At least 1000 random instances per configuration
- 6–8 arguments per instance
- Each possible attack (a, b) with a ≠ b present independently with probability
  **p**, swept over p ∈ {0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5}. A second run
  also allows self-attacks.
- Arguments assigned to agents uniformly at random

For each instance, record:

- whether the mechanism is strategyproof (Theorem 5.3 test)
- whether the Theorem 5.4 condition holds (both cycle interpretations)

### Research questions

| # | Question | Expectation |
|---|---|---|
| Q1 | What fraction of instances is strategyproof, for each p? | Reported as a table and a plot |
| Q2 | How many instances satisfy the Thm 5.4 condition yet **fail** strategyproofness? | None, if the theorem holds under the chosen path interpretation. Any found are saved and explained |
| Q3 | Are there instances that are strategyproof **although** the condition fails? | Yes, because the condition is sufficient but not necessary. Examples are saved and the reason is analysed (for example, a harmful chain cancelled by another argument, as in Example 5.11) |

Brute-force cost per instance is roughly Σᵢ 2^(n − |Aᵢ|) · 2^|Aᵢ| = 3 · 2ⁿ
grounded computations, at most 768 for n = 8. This is cheap enough to run
thousands of instances.

Each Q3 instance is labelled automatically with one of three reasons:

| Reason | Meaning |
|---|---|
| `rescue_costs_as_much` | Some deviation gets a rejected own argument accepted, but every such deviation loses at least as many own arguments |
| `never_rescues` | No deviation, against any reports by the others, gets a rejected own argument accepted; the odd path is always cancelled (as in Example 5.11) |
| `self_cycles_only` | The only violations are α ↪ α (odd cycles through a single argument), which hiding cannot exploit |

### Outputs

`experiments/run_experiments.py` writes to `results/` (and
`results/self-attacks/` with `--self-attacks`):

| File | Contents |
|---|---|
| `summary.csv` | Per-p counts: strategyproof, condition holds (both readings), Q2, Q3, Q3 reasons |
| `strategyproofness_by_p.png` | Plot of the strategyproof and condition-holds fractions against p |
| `q2_walk.json`, `q2_simple.json` | Every Q2 instance |
| `q3_examples.json` | The 10 smallest Q3 instances for each reason |
| `instances.jsonl` | Every instance (not committed; regenerated exactly from `config.json` and the seed) |

### Exhaustive verification

`experiments/exhaustive.py` complements the random experiments by checking
every directed graph on up to 5 arguments against every possible argument set
for one agent. With disjoint types, the other agents can jointly reveal any
subset of the remaining arguments, so strategyproofness for an agent depends
only on the graph and its own set. Results are in `results/exhaustive/` and
`results/exhaustive-self-attacks/`.

---

## 5. Deliverables

| Deliverable | Contents | Status |
|---|---|---|
| **Code** | Library, test suite built from textbook examples, experiment runner | ✅ Done |
| **README** | Overview, installation, usage, and how to run tests, demo and experiments | ✅ Done |
| **Report** | Definitions, design decisions (including cycle handling), validation results, experiment tables and plots, analysis of Q2/Q3 instances, errata | ⏸ Pending |
| **Demonstration** | A walkthrough script covering the textbook examples and the strategic manipulation cases | ✅ Done (`demo.py`) |
