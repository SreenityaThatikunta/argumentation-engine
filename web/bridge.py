"""JSON bridge between the web demo and the argumentation library.

Runs inside Pyodide. The page calls ``call(name, payload)`` with a JSON
payload and gets a JSON string back; every function below works on plain
lists and dicts so nothing Python-specific crosses into JavaScript.
"""

from __future__ import annotations

import json
import random
import re

from argumentation import ArgumentationFramework, acceptance_report, extensions
from argumentation.labelling import extension_to_labelling
from argumentation.strategic import Game, induced_framework, theorem_5_4_violations
from experiments.run_experiments import evaluate, explain_strategyproof, generate_instance


def natural(arg) -> tuple:
    return tuple(int(t) if t.isdigit() else t for t in re.split(r"(\d+)", str(arg)))


def ordered(args) -> list:
    return sorted(args, key=natural)


def labels(af, s) -> dict:
    return {a: str(lab) for a, lab in extension_to_labelling(af, s).items()}


def framework(arguments, attacks) -> ArgumentationFramework:
    return ArgumentationFramework(arguments, [tuple(a) for a in attacks])


def analyse(arguments, attacks, semantics):
    """Extensions, their labellings, acceptance status and the F(S) iteration."""
    af = framework(arguments, attacks)
    exts = extensions(af, semantics)
    steps, s = [], frozenset()
    while True:
        nxt = af.characteristic(s)
        steps.append({"set": ordered(nxt), "labelling": labels(af, nxt), "fixed": nxt == s})
        if nxt == s:
            break
        s = nxt
    return {
        "extensions": [ordered(e) for e in exts],
        "labellings": [labels(af, e) for e in exts],
        "status": {str(a): str(st) for a, st in acceptance_report(af, semantics).items()},
        "steps": steps,
    }


def check_set(arguments, attacks, members):
    af = framework(arguments, attacks)
    s = frozenset(members)
    return {
        "conflict_free": af.is_conflict_free(s),
        "admissible": af.is_admissible(s),
        "complete": af.is_complete(s),
        "characteristic": ordered(af.characteristic(s)),
        "plus": ordered(af.plus(s)),
    }


def game_state(attacks, types, reports):
    """Outcome of the mechanism for the given reports, next to the truthful one."""
    game = Game([tuple(a) for a in attacks], types)
    reports = {agent: frozenset(r) for agent, r in reports.items()}
    revealed = frozenset().union(*reports.values())
    outcome = game.outcome(reports)
    truthful = game.outcome(game.types)
    return {
        "outcome": ordered(outcome),
        "truthful_outcome": ordered(truthful),
        "labelling": labels(induced_framework(game.attacks, revealed), outcome),
        "utilities": {
            agent: {"truthful": len(truthful & own), "now": len(outcome & own)}
            for agent, own in game.types.items()
        },
    }


def best_response(attacks, types, reports, agent):
    """Best reports for ``agent`` against the others' current reports.

    Among equally good reports, the one hiding the fewest arguments comes first.
    """
    game = Game([tuple(a) for a in attacks], types)
    br = game.best_responses(agent, {a: r for a, r in reports.items() if a != agent})
    best = sorted(br.reports, key=lambda r: (-len(r), ordered(r)))
    return {"utility": br.utility, "reports": [ordered(r) for r in best]}


def theorems(attacks, types):
    """Exact Theorem 5.3 check plus the Theorem 5.4 condition under both readings."""
    attacks = [tuple(a) for a in attacks]
    game = Game(attacks, types)
    witness = next(game.manipulations(), None)
    result = {"strategyproof": witness is None, "manipulation": None}
    if witness is not None:
        result["manipulation"] = {
            "agent": witness.agent,
            "others": {a: ordered(r) for a, r in witness.others.items()},
            "report": ordered(witness.report),
            "hidden": ordered(witness.hidden),
            "truthful_utility": witness.truthful_utility,
            "manipulated_utility": witness.manipulated_utility,
        }
    for mode in ("walk", "simple"):
        result[f"violations_{mode}"] = [
            list(v) for v in theorem_5_4_violations(attacks, types, mode)
        ]
    if witness is None and result["violations_walk"]:
        result["q3_reason"] = explain_strategyproof(game, result["violations_walk"])
    return result


def random_instance(p, seed, min_args=6, max_args=8):
    rng = random.Random(seed)
    args, attacks, types = generate_instance(rng, p, range(min_args, max_args + 1), False)
    return {"arguments": args, "attacks": [list(a) for a in attacks], "types": types}


def sample(p, seed):
    """One random instance from the experiment generator, evaluated."""
    rng = random.Random(seed)
    args, attacks, types = generate_instance(rng, p, range(6, 9), False)
    record = evaluate(seed, p, args, attacks, types)
    return {
        "strategyproof": record["strategyproof"],
        "thm54_walk": record["thm54_walk"],
        "thm54_simple": record["thm54_simple"],
        "q3_reason": record.get("q3_reason"),
    }


FUNCTIONS = {
    f.__name__: f
    for f in (analyse, check_set, game_state, best_response, theorems, random_instance, sample)
}


def call(name: str, payload: str) -> str:
    return json.dumps(FUNCTIONS[name](**json.loads(payload)))
