"""Guided walkthrough of the Argumentation Engine.

Covers every part of the project on the textbook examples (Rahwan,
"Argumentation among Agents", Chapter 5 of Weiss, Multiagent Systems):

  1. Argumentation framework: conflict-freeness, defence, F(S), admissible, complete
  2. Semantics, labellings and acceptance status
  3. Strategic argumentation on Example 5.10
  4. Example 5.11: strategyproof although Theorem 5.4's condition fails
  5. Cycles and the two readings of "odd-length path"
  6. Random experiments (Q1-Q3)
  7. Exhaustive verification of Theorem 5.4

Usage:
    python demo.py              # pauses between sections
    python demo.py --no-pause   # runs straight through
    python demo.py --section 3  # one section only

Figures are written to demo_output/ when Graphviz is installed.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import shutil
from collections.abc import Callable, Iterable
from pathlib import Path

from argumentation import (
    ArgumentationFramework,
    acceptance_report,
    complete_extensions,
    grounded,
    legal_labellings,
    preferred_extensions,
    semi_stable_extensions,
    stable_extensions,
)
from argumentation.examples import example_5_10, example_5_11, figure_5_1, figure_5_2
from argumentation.labelling import grounded_labelling
from argumentation.strategic import (
    Game,
    indirect_defeats,
    mechanism,
    theorem_5_4_violations,
    utility,
)
from argumentation.visualize import mechanism_dot, render, to_dot
from experiments.exhaustive import check_range, edge_list
from experiments.run_experiments import evaluate, generate_instance, summarise

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


class Demo:
    def __init__(self, pause: bool, out: Path):
        self.pause_enabled = pause
        self.out = out
        self.can_render = shutil.which("dot") is not None

    # -- output helpers -----------------------------------------------------

    def section(self, number: int, title: str) -> None:
        print()
        print("=" * 72)
        print(f" {number}. {title}")
        print("=" * 72)

    def step(self, text: str) -> None:
        print(f"\n> {text}")

    def show(self, label: str, value: object) -> None:
        print(f"    {label:<34} {value}")

    def note(self, text: str) -> None:
        print(f"    # {text}")

    def pause(self) -> None:
        if self.pause_enabled:
            input("\n[press Enter to continue]")

    def figure(self, dot_source: str, name: str) -> None:
        if not self.can_render:
            self.note(f"(Graphviz not installed; skipped figure {name})")
            return
        self.out.mkdir(parents=True, exist_ok=True)
        path = render(dot_source, self.out / f"{name}.svg")
        self.note(f"figure: {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")

    # -- sections -----------------------------------------------------------

    def framework_basics(self) -> None:
        self.section(1, "Argumentation framework (Figure 5.1)")
        af = figure_5_1()
        self.step("Figure 5.1: α2 and α4 attack α1; α3 attacks α2; α5 attacks α4")
        self.show("arguments", fmt(af.arguments))
        self.show("attacks", ", ".join(f"{g(a)}⇀{g(b)}" for a, b in sorted(af.attacks)))

        self.step("Conflict-free (Def 5.2): no member attacks another")
        self.show("{α1, α3, α5} conflict-free?", af.is_conflict_free({"a1", "a3", "a5"}))
        self.show("{α2, α3} conflict-free?", af.is_conflict_free({"a2", "a3"}))

        self.step("Defence (Def 5.2): S attacks every attacker of the argument")
        self.show("{α3, α5} defends α1?", af.defends({"a3", "a5"}, "a1"))
        self.show("{α3} defends α1?", af.defends({"a3"}, "a1"))
        self.note("α4 also attacks α1, and only α5 attacks α4")

        self.step("Characteristic function F(S) (Def 5.3), iterated from ∅")
        s: frozenset = frozenset()
        for i in range(1, 4):
            nxt = af.characteristic(s)
            self.show(f"F^{i}(∅)", fmt(nxt) + ("   <- fixed point" if nxt == s else ""))
            s = nxt
        self.note("the fixed point is the grounded extension")

        self.step("Admissible (Def 5.4) vs complete (Def 5.5), Examples 5.5 and 5.6")
        for subset in ({"a3", "a5"}, {"a1", "a3", "a5"}):
            self.show(
                f"{fmt(subset)}",
                f"admissible={af.is_admissible(subset)}, complete={af.is_complete(subset)}",
            )
        self.note("{α3, α5} defends α1 without containing it, so it is not complete")
        self.figure(to_dot(af, grounded_labelling(af), title="Figure 5.1"), "1_figure_5_1")
        self.pause()

    def semantics(self) -> None:
        self.section(2, "Semantics, labellings and acceptance (Figure 5.2)")
        af = figure_5_2()
        self.step("Figure 5.2: α1 and α2 attack each other; α3 is unattacked")
        self.show("grounded", fmt(grounded(af)))
        self.show("complete", fmt_all(complete_extensions(af)))
        self.show("preferred", fmt_all(preferred_extensions(af)))
        self.show("stable", fmt_all(stable_extensions(af)))
        self.show("semi-stable", fmt_all(semi_stable_extensions(af)))

        self.step("Legal labellings (Def 5.6): one per complete extension")
        for i, lab in enumerate(legal_labellings(af), 1):
            self.show(f"L{i}", "  ".join(f"{g(a)}={lab[a]}" for a in sorted(lab, key=_natural)))
            self.figure(to_dot(af, lab, title=f"Figure 5.2, labelling {i}"), f"2_labelling_{i}")

        self.step("Acceptance status (Def 5.8) under preferred semantics")
        for arg, status in acceptance_report(af, "preferred").items():
            self.show(g(arg), status)

        self.step("Edge case: a ⇄ b, b ⇀ c, c ⇀ c, plus an isolated 3-cycle x ⇀ y ⇀ z ⇀ x")
        edge = ArgumentationFramework(
            "abcxyz",
            [("a", "b"), ("b", "a"), ("b", "c"), ("c", "c"), ("x", "y"), ("y", "z"), ("z", "x")],
        )
        self.show("preferred", fmt_all(preferred_extensions(edge)))
        self.show("stable", fmt_all(stable_extensions(edge)) + "   <- the 3-cycle rules it out")
        self.show("semi-stable", fmt_all(semi_stable_extensions(edge)))
        self.note("{b} also defeats c, so its range S ∪ S⁺ is larger than {a}'s")
        self.pause()

    def example_5_10(self) -> None:
        self.section(3, "Strategic argumentation (Example 5.10)")
        attacks, types = example_5_10()
        self.step("Agents and their private arguments")
        for agent, args in types.items():
            self.show(f"agent {agent}", fmt(args))
        self.show("attacks", ", ".join(f"{g(a)}⇀{g(b)}" for a, b in sorted(attacks)))

        self.step("Mechanism (Def 5.21): grounded extension of everything revealed")
        outcome = mechanism(attacks, types)
        self.show("truthful outcome", fmt(outcome))
        for agent, args in types.items():
            self.show(f"utility of {agent}", utility(outcome, args))
        self.note("errata: the book swaps y and z here; y holds α2 (0), z holds α3 (1)")
        self.figure(mechanism_dot(attacks, types, types, "Example 5.10: truthful"), "3_truthful")

        game = Game(attacks, types)
        self.step("Best response of x against truthful y and z")
        br = game.best_responses("x", {"y": types["y"], "z": types["z"]})
        self.show("best utility", br.utility)
        self.show("best reports", fmt_all(br.reports))
        hiding = {**types, "x": types["x"] - {"a1"}}
        self.show("outcome if x hides α1", fmt(mechanism(attacks, hiding)))
        self.note("hiding α1 lets α2 defeat α3, which frees α4 and α5")
        self.figure(mechanism_dot(attacks, types, hiding, "Example 5.10: x hides α1"), "3_hiding")

        self.step("Theorem 5.3: exhaustive strategyproofness check")
        self.show("strategyproof?", game.is_strategyproof())
        manipulations = list(game.manipulations())
        self.show("profitable deviations found", len(manipulations))
        m = manipulations[0]
        others = ", ".join(f"{a} reveals {fmt(r)}" for a, r in m.others.items())
        self.show("example", f"{others}: x hides {fmt(m.hidden)}")
        self.show("", f"utility {m.truthful_utility} -> {m.manipulated_utility}")

        self.step("Theorem 5.4: no agent may hold α, β with an odd path α ⇝ β")
        for who, a, b in theorem_5_4_violations(attacks, types):
            self.show(f"violation by {who}", f"{g(a)} ↪ {g(b)}")
        self.pause()

    def example_5_11(self) -> None:
        self.section(4, "Example 5.11: the condition is sufficient, not necessary")
        attacks, types = example_5_11()
        self.step("Example 5.10 plus α6 ∈ Aₓ with α6 ⇀ α3")
        outcome = mechanism(attacks, types)
        self.show("truthful outcome", fmt(outcome))
        self.show("utility of x", f"{utility(outcome, types['x'])} of {len(types['x'])}")
        self.show("strategyproof?", Game(attacks, types).is_strategyproof())
        violations = theorem_5_4_violations(attacks, types)
        self.show("Theorem 5.4 holds?", not violations)
        self.show(
            "violations", ", ".join(f"{g(a)} ↪ {g(b)}" for agent, a, b in violations if a != b)
        )
        self.note("errata: α6 (not α5) cancels the self-defeat, by attacking α3")
        self.figure(mechanism_dot(attacks, types, types, "Example 5.11"), "4_example_5_11")
        self.pause()

    def cycles(self) -> None:
        self.section(5, 'Cycles and the two readings of "odd-length path"')
        attacks = {("g", "u"), ("u", "v"), ("v", "w"), ("w", "u"), ("u", "t")}
        self.step("g ⇀ u, a 3-cycle u ⇀ v ⇀ w ⇀ u, and u ⇀ t")
        self.show("simple paths g to t", "g→u→t (length 2, even)")
        self.show("walks g to t", "also g→u→v→w→u→t (length 5, odd)")
        walk = ("g", "t") in indirect_defeats(attacks, "guvwt", "walk")
        simple = ("g", "t") in indirect_defeats(attacks, "guvwt", "simple")
        self.show("g ↪ t with walks?", walk)
        self.show("g ↪ t with simple paths?", simple)
        self.note("walks are searched over (argument, parity) states, so cycles terminate")
        self.note("the walk reading is stricter; both are implemented and compared")
        self.pause()

    def experiments(self) -> None:
        self.section(6, "Random experiments (Q1-Q3)")
        self.step("Live mini-run: 50 instances per p (3 agents, 6-8 arguments)")
        rng = random.Random(7)
        ps = [0.1, 0.2, 0.3]
        records: list[dict] = []
        for p in ps:
            for _ in range(50):
                args, attacks, types = generate_instance(rng, p, range(6, 9), False)
                records.append(evaluate(len(records), p, args, attacks, types))
        for row in summarise(records, ps):
            self.show(
                f"p = {row['p']}",
                f"strategyproof {row['strategyproof_fraction']:.0%}, Q2 = {row['q2_walk']}, "
                f"Q3 = {row['q3_walk']}",
            )

        summary = RESULTS / "summary.csv"
        if not summary.exists():
            self.note("run experiments/run_experiments.py to see the full results")
            self.pause()
            return
        self.step("Full results: 1000 instances per p (results/summary.csv)")
        self.show("p", "strategyproof   condition holds   Q2   Q3")
        with summary.open() as f:
            for row in csv.DictReader(f):
                n = int(row["instances"])
                self.show(
                    row["p"],
                    f"{int(row['strategyproof']) / n:>12.1%}   {int(row['thm54_walk']) / n:>14.1%}"
                    f"   {row['q2_walk']:>2}   {row['q3_walk']:>3}",
                )
        self.note("Q1: strategyproofness falls quickly as attacks become denser")
        self.note("Q2: zero instances satisfy the condition yet fail strategyproofness")

        self.step("Q3: why strategyproof instances escape the condition")
        examples = json.loads((RESULTS / "q3_examples.json").read_text())
        for reason, explain in (
            ("rescue_costs_as_much", self._explain_costly_rescue),
            ("never_rescues", self._explain_never_rescues),
            ("self_cycles_only", self._explain_self_cycles),
        ):
            if examples.get(reason):
                explain(examples[reason][0])
        self.pause()

    def _instance(self, record: dict) -> tuple[list[tuple[str, str]], dict[str, list[str]]]:
        attacks = [(a, b) for a, b in record["attacks"]]
        self.show("attacks", ", ".join(f"{g(a)}⇀{g(b)}" for a, b in attacks))
        self.show("types", "  ".join(f"{k}={fmt(v)}" for k, v in record["types"].items()))
        return attacks, record["types"]

    def _explain_costly_rescue(self, record: dict) -> None:
        print("\n  [rescue_costs_as_much]")
        attacks, types = self._instance(record)
        agent, a, b = next(v for v in record["violations_walk"] if v[1] != v[2])
        self.show("violation", f"{agent}: {g(a)} ↪ {g(b)}")
        game = Game(attacks, types)
        own = game.types[agent]
        others = {k: v for k, v in game.types.items() if k != agent}
        truthful = game.outcome({**others, agent: own})
        hiding = game.outcome({**others, agent: own - {a}})
        self.show(f"{agent} truthful", f"accepted {fmt(truthful & own)}")
        self.show(f"{agent} hides {g(a)}", f"accepted {fmt(hiding & own)}")
        gained, lost = (hiding - truthful) & own, (truthful - hiding) & own
        self.note(f"hiding {g(a)} gains {fmt(gained)} but loses {fmt(lost)}")
        self.note("every rescuing deviation costs at least as much, so none strictly gains")

    def _explain_never_rescues(self, record: dict) -> None:
        print("\n  [never_rescues]")
        self._instance(record)
        agent, a, b = next(v for v in record["violations_walk"] if v[1] != v[2])
        self.show("violation", f"{agent}: {g(a)} ↪ {g(b)}")
        self.note(f"for every report by the others, no hiding by {agent} turns a rejected")
        self.note("own argument into an accepted one, so the odd path never bites")

    def _explain_self_cycles(self, record: dict) -> None:
        print("\n  [self_cycles_only]")
        self._instance(record)
        cycles = ", ".join(f"{g(a)} ↪ {g(a)}" for _, a, _ in record["violations_walk"])
        self.show("violations", cycles)
        self.note("an odd cycle back to the same argument cannot be exploited by hiding")

    def exhaustive(self) -> None:
        self.section(7, "Exhaustive verification of Theorem 5.4")
        self.step("Live: every graph on up to 4 arguments x every agent argument set")
        for n in range(1, 5):
            tallies = check_range((n, False, 0, 1 << len(edge_list(n, False))))
            pairs = sum(t.pairs for t in tallies.values())
            q2w = sum(t.q2_walk for t in tallies.values())
            q2s = sum(t.q2_simple for t in tallies.values())
            self.show(f"n = {n}", f"{pairs:>6} pairs checked, Q2 walk = {q2w}, Q2 simple = {q2s}")

        for name, label in (
            ("exhaustive", "n ≤ 5, no self-attacks"),
            ("exhaustive-self-attacks", "n ≤ 5, with self-attacks"),
        ):
            path = RESULTS / name / "summary.csv"
            if path.exists():
                rows = list(csv.DictReader(path.open()))
                pairs = sum(int(r["pairs"]) for r in rows)
                q2 = sum(int(r["q2_walk"]) + int(r["q2_simple"]) for r in rows)
                self.show(f"saved: {label}", f"{pairs:,} pairs, counterexamples = {q2}")
        self.note("no counterexample to Theorem 5.4 under either reading of odd path")


SECTIONS: list[Callable[[Demo], None]] = [
    Demo.framework_basics,
    Demo.semantics,
    Demo.example_5_10,
    Demo.example_5_11,
    Demo.cycles,
    Demo.experiments,
    Demo.exhaustive,
]


def g(arg: object) -> str:
    """Display a1 as α1, leaving other names unchanged."""
    return re.sub(r"^a(\d+)$", r"α\1", str(arg))


def fmt(args: Iterable) -> str:
    return "{" + ", ".join(g(a) for a in sorted(args, key=_natural)) + "}"


def fmt_all(sets: Iterable[Iterable]) -> str:
    sets = list(sets)
    return ", ".join(fmt(s) for s in sets) if sets else "none"


def _natural(arg: object) -> tuple:
    return tuple(int(t) if t.isdigit() else t for t in re.split(r"(\d+)", str(arg)))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--no-pause", action="store_true", help="do not wait between sections")
    parser.add_argument("--section", type=int, choices=range(1, len(SECTIONS) + 1))
    parser.add_argument("--out", type=Path, default=ROOT / "demo_output")
    opts = parser.parse_args(argv)

    demo = Demo(pause=not opts.no_pause, out=opts.out)
    chosen = [SECTIONS[opts.section - 1]] if opts.section else SECTIONS
    for run in chosen:
        run(demo)
    print("\nDone.")


if __name__ == "__main__":
    main()
