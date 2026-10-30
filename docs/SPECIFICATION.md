# Project Specification

This document defines the scope of the Argumentation Engine: the reasoning
library, the strategic-argumentation (mechanism design) module, the
experiments, and the deliverables.

All definitions follow **Chapter 5, "Argumentation among Agents" (Iyad Rahwan)**
in *Multiagent Systems*, 2nd edition, edited by Gerhard Weiss (MIT Press, 2013).
Definition, theorem and example numbers below refer to that chapter.

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
acceptable?"*

| # | Component | Input → Output | Book |
|---|---|---|---|
| 1 | `ArgumentationFramework` class | arguments + attack pairs → framework object | Def 5.1 |
| 2 | `is_conflict_free(S)` | set S → bool. No member of S attacks another member | Def 5.2 |
| 3 | `defends(S, a)` | set S, argument a → bool. Every attacker of a is attacked by S (α⁻ ⊆ S⁺) | Def 5.2 |
| 4 | `characteristic(S)`, written F(S) | set S → the set of all arguments S defends | Def 5.3 |
| 5 | `is_admissible(S)`, `is_complete(S)` | set S → bool. Admissible: conflict-free and S ⊆ F(S). Complete: conflict-free and S = F(S) | Def 5.4, 5.5 |
| 6A | `grounded()` | iterate F from ∅ until a fixed point → one set (the least complete extension) | Def 5.7 |
| 6B | `complete_extensions()` | → every conflict-free S with S = F(S) | Def 5.5 |
| 6C | `preferred()`, `stable()`, `semi_stable()` | **Preferred:** ⊆-maximal complete extensions. **Stable:** S⁺ = A \ S. **Semi-stable:** complete extensions with ⊆-maximal S ∪ S⁺ | Def 5.7 |
| 6D | `labellings()` | → every legal labelling. An argument is `in` iff all its attackers are `out`, `out` iff some attacker is `in`, and `undec` otherwise. Labellings correspond one-to-one with complete extensions | Def 5.6, Table 5.1 |
| 6E | `acceptance_status(a, semantics)` | argument → **skeptically accepted** (in every extension), **credulously accepted** (in at least one), or **rejected** (in none) | Def 5.8 |

### Validation against the textbook

| Source | Graph | Expected results |
|---|---|---|
| Figure 5.1, Examples 5.5, 5.6, 5.8 | α2 ⇀ α1, α4 ⇀ α1, α3 ⇀ α2, α5 ⇀ α4 | {α1, α3, α5} is admissible. {α3, α5} is admissible but not complete. F({α3}) = {α3, α5}. Grounded is reached via F¹(∅) = {α3, α5}, F²(∅) = {α1, α3, α5}. This set is the only complete and the only preferred extension |
| Figure 5.2, Examples 5.7, 5.8 | α1 ⇄ α2, α3 unattacked | Complete extensions are {α3}, {α1, α3} and {α2, α3}. Grounded is {α3}. Preferred extensions are {α1, α3} and {α2, α3} |
| Figure 5.3 | arguments a–e (edges taken from the figure) | Grounded is {a, c, e} |

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

| # | Component | Description | Book |
|---|---|---|---|
| 1 | `mechanism(attacks, reports)` | Takes the global attack relation and one revealed set per agent. Returns the grounded extension of the graph induced by the union of the reports | Def 5.21 |
| 2 | `best_responses(agent, reports)` | Fixes the other agents' reports, enumerates all 2^\|Aᵢ\| subsets the agent could reveal, and returns those that maximise its utility | Def 5.22 |
| 3 | `is_strategyproof(...)` | **Theorem 5.3, the exact test.** For every agent and every combination of subsets the other agents could reveal, revealing all of Aᵢ (truthfulness) must be a best response | Thm 5.3 |
| 4 | `satisfies_thm_5_4(...)` | **Theorem 5.4, the sufficient graph condition.** No agent holds two arguments α, β with an odd-length directed path from α to β in the full graph. Must handle cycles correctly | Thm 5.4 |

### Handling cycles in Theorem 5.4

"Odd-length path" is ambiguous when the graph contains cycles:

- **Walks (vertices may repeat).** Search over states `(node, parity)`. This is
  polynomial, but going around an odd cycle can flip the parity, so the same
  pair can have both odd and even connections.
- **Simple paths (no repeated vertices).** Requires enumerating paths. This is
  feasible for graphs of 6–8 arguments.

Both interpretations are implemented and compared in the experiments. Whether
the condition applies to α = β (self-attacks, odd cycles through a single
argument) is documented explicitly.

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

---

## 5. Deliverables

| Deliverable | Contents |
|---|---|
| **Code** | Library, test suite built from textbook examples, experiment runner |
| **README** | Overview, installation, usage, and how to run tests, demo and experiments |
| **Report** | Definitions, design decisions (including cycle handling), validation results, experiment tables and plots, analysis of Q2/Q3 instances, errata |
| **Demonstration** | A walkthrough script covering the textbook examples and the strategic manipulation cases |
