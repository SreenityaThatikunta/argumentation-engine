"""Random-instance experiments for the grounded direct argumentation mechanism.

For each attack probability p, generates random instances (6-8 arguments,
3 agents, each possible attack present with probability p, arguments split
uniformly at random among agents) and records:

* whether the mechanism is strategyproof (exhaustive Theorem 5.3 check), and
* whether Theorem 5.4's condition holds, under both readings of
  "odd-length path" (walks that may revisit arguments, and simple paths).

Usage:
    python experiments/run_experiments.py --instances 1000 --out results
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import time
from collections import Counter
from itertools import product
from pathlib import Path

from argumentation.strategic import Game, subsets, theorem_5_4_violations

AGENTS = ("x", "y", "z")
PATH_MODES = ("walk", "simple")
Q3_REASONS = ("rescue_costs_as_much", "never_rescues", "self_cycles_only")
Q3_SAMPLE = 10


def generate_instance(rng: random.Random, p: float, sizes: range, self_attacks: bool):
    n = rng.choice(sizes)
    args = [f"a{i}" for i in range(1, n + 1)]
    attacks = sorted(
        (a, b) for a in args for b in args if (self_attacks or a != b) and rng.random() < p
    )
    types: dict[str, list[str]] = {agent: [] for agent in AGENTS}
    for a in args:
        types[rng.choice(AGENTS)].append(a)
    return args, attacks, types


def explain_strategyproof(game: Game, violations: list[tuple]) -> str:
    """Why a strategyproof instance escapes despite failing Theorem 5.4.

    * ``self_cycles_only``: the only violations are α ↪ α (an odd cycle
      through a single argument), which hiding cannot exploit.
    * ``rescue_costs_as_much``: some deviation gets a previously rejected own
      argument accepted, but every such deviation loses at least as many
      own arguments (typically the hidden ones).
    * ``never_rescues``: no deviation, against any reports by the others,
      gets a rejected own argument accepted; the odd path is always cancelled
      or the target is lost for other reasons (as in Example 5.11).
    """
    agents = {agent for agent, a, b in violations if a != b}
    if not agents:
        return "self_cycles_only"
    for i in agents:
        others = [a for a in game.types if a != i]
        for combo in product(*(list(subsets(game.types[a])) for a in others)):
            fixed = dict(zip(others, combo, strict=True))
            truthful = game.outcome({**fixed, i: game.types[i]})
            for report in subsets(game.types[i]):
                gained = (game.outcome({**fixed, i: report}) - truthful) & game.types[i]
                if gained:
                    return "rescue_costs_as_much"
    return "never_rescues"


def evaluate(instance_id: int, p: float, args, attacks, types) -> dict:
    game = Game(attacks, types)
    witness = next(game.manipulations(), None)
    record = {
        "id": instance_id,
        "p": p,
        "n": len(args),
        "attacks": attacks,
        "types": types,
        "strategyproof": witness is None,
        "truthful_outcome": sorted(game.outcome(types), key=str),
    }
    if witness is not None:
        record["manipulation"] = {
            "agent": witness.agent,
            "others": {a: sorted(r) for a, r in witness.others.items()},
            "report": sorted(witness.report),
            "hidden": sorted(witness.hidden),
            "truthful_utility": witness.truthful_utility,
            "manipulated_utility": witness.manipulated_utility,
        }
    for mode in PATH_MODES:
        violations = theorem_5_4_violations(attacks, types, mode)
        record[f"thm54_{mode}"] = not violations
        record[f"violations_{mode}"] = [list(v) for v in violations]
    if record["strategyproof"] and not record["thm54_walk"]:
        record["q3_reason"] = explain_strategyproof(game, record["violations_walk"])
    return record


def summarise(records: list[dict], ps: list[float]) -> list[dict]:
    rows = []
    for p in ps:
        rs = [r for r in records if r["p"] == p]
        sp = [r for r in rs if r["strategyproof"]]
        row = {
            "p": p,
            "instances": len(rs),
            "strategyproof": len(sp),
            "strategyproof_fraction": round(len(sp) / len(rs), 4),
        }
        for mode in PATH_MODES:
            cond = [r for r in rs if r[f"thm54_{mode}"]]
            row[f"thm54_{mode}"] = len(cond)
            # Q2: condition holds, yet not strategyproof.
            row[f"q2_{mode}"] = sum(not r["strategyproof"] for r in cond)
            # Q3: strategyproof, although the condition fails.
            row[f"q3_{mode}"] = sum(r["strategyproof"] and not r[f"thm54_{mode}"] for r in rs)
        row["walk_simple_disagree"] = sum(r["thm54_walk"] != r["thm54_simple"] for r in rs)
        reasons = Counter(r.get("q3_reason") for r in rs)
        for reason in Q3_REASONS:
            row[f"q3_{reason}"] = reasons[reason]
        rows.append(row)
    return rows


def write_outputs(out: Path, records: list[dict], rows: list[dict], config: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(config, indent=2) + "\n")

    with (out / "instances.jsonl").open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    with (out / "summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    for mode in PATH_MODES:
        q2 = [r for r in records if r[f"thm54_{mode}"] and not r["strategyproof"]]
        (out / f"q2_{mode}.json").write_text(json.dumps(q2, indent=1) + "\n")

    # A readable sample of Q3 instances per reason, smallest graphs first;
    # the full set is in instances.jsonl.
    q3 = sorted(
        (r for r in records if "q3_reason" in r),
        key=lambda r: (len(r["attacks"]) + r["n"], r["id"]),
    )
    sample = {
        reason: [r for r in q3 if r["q3_reason"] == reason][:Q3_SAMPLE] for reason in Q3_REASONS
    }
    (out / "q3_examples.json").write_text(json.dumps(sample, indent=1) + "\n")

    _plot(out, rows)


def _plot(out: Path, rows: list[dict]) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping plot")
        return

    ps = [r["p"] for r in rows]
    n = [r["instances"] for r in rows]
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.plot(
        ps,
        [r["strategyproof"] / k for r, k in zip(rows, n, strict=True)],
        "o-",
        label="Strategyproof (Thm 5.3)",
    )
    ax.plot(
        ps,
        [r["thm54_walk"] / k for r, k in zip(rows, n, strict=True)],
        "s--",
        label="Thm 5.4 condition (walks)",
    )
    ax.plot(
        ps,
        [r["thm54_simple"] / k for r, k in zip(rows, n, strict=True)],
        "^:",
        label="Thm 5.4 condition (simple paths)",
    )
    ax.set_xlabel("Attack probability p")
    ax.set_ylabel("Fraction of instances")
    ax.set_ylim(0, 1.02)
    ax.set_xticks(ps)
    ax.grid(alpha=0.3)
    ax.legend()
    ax.set_title("Grounded direct mechanism, 3 agents, 6-8 arguments")
    fig.tight_layout()
    fig.savefig(out / "strategyproofness_by_p.png", dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--instances", type=int, default=1000, help="instances per value of p")
    parser.add_argument("--p", type=float, nargs="+", default=[0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5])
    parser.add_argument("--min-args", type=int, default=6)
    parser.add_argument("--max-args", type=int, default=8)
    parser.add_argument(
        "--self-attacks", action="store_true", help="allow arguments to attack themselves"
    )
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--out", type=Path, default=Path("results"))
    opts = parser.parse_args()

    rng = random.Random(opts.seed)
    sizes = range(opts.min_args, opts.max_args + 1)
    records: list[dict] = []
    start = time.perf_counter()
    for p in opts.p:
        for _ in range(opts.instances):
            args, attacks, types = generate_instance(rng, p, sizes, opts.self_attacks)
            records.append(evaluate(len(records), p, args, attacks, types))
        print(f"p={p}: done ({time.perf_counter() - start:.1f}s)")

    rows = summarise(records, opts.p)
    config = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(opts).items()}
    write_outputs(opts.out, records, rows, config)

    header = list(rows[0])
    print("\n" + " | ".join(header))
    for row in rows:
        print(" | ".join(str(row[h]) for h in header))


if __name__ == "__main__":
    main()
