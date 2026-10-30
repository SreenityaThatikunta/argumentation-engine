"""Render the textbook examples and result plots (requires Graphviz).

Usage:
    python experiments/figures.py                                   # SVGs for docs/figures/
    python experiments/figures.py --format pdf --no-titles --out report/figures
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from argumentation.examples import example_5_10, example_5_11, figure_5_1, figure_5_2
from argumentation.labelling import grounded_labelling, legal_labellings
from argumentation.visualize import mechanism_dot, render, to_dot

ROOT = Path(__file__).resolve().parent.parent


def render_examples(out: Path, fmt: str, titles: bool) -> None:
    def title(text: str) -> str | None:
        return text if titles else None

    af = figure_5_1()
    render(
        to_dot(af, grounded_labelling(af), title=title("Figure 5.1: grounded labelling")),
        out / f"figure_5_1.{fmt}",
    )

    af = figure_5_2()
    for i, lab in enumerate(legal_labellings(af), 1):
        text = title(f"Figure 5.2: complete labelling {i} of 3")
        render(to_dot(af, lab, title=text), out / f"figure_5_2_labelling_{i}.{fmt}")

    attacks, types = example_5_10()
    render(
        mechanism_dot(attacks, types, types, title("Example 5.10: all agents truthful (x gets 1)")),
        out / f"example_5_10_truthful.{fmt}",
    )
    hiding = {**types, "x": types["x"] - {"a1"}}
    render(
        mechanism_dot(attacks, types, hiding, title("Example 5.10: x hides a1 (x gets 2)")),
        out / f"example_5_10_x_hides_a1.{fmt}",
    )

    attacks, types = example_5_11()
    render(
        mechanism_dot(
            attacks, types, types, title("Example 5.11: a6 cancels the self-defeat (x gets 4)")
        ),
        out / f"example_5_11_truthful.{fmt}",
    )


def plot_results(out: Path, fmt: str) -> None:
    """Strategyproof and condition-holds fractions, with and without self-attacks."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping results plot")
        return

    runs = [("results", "no self-attacks", "-"), ("results/self-attacks", "self-attacks", "--")]
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    for folder, label, style in runs:
        path = ROOT / folder / "summary.csv"
        if not path.exists():
            continue
        rows = list(csv.DictReader(path.open()))
        ps = [float(r["p"]) for r in rows]
        n = [int(r["instances"]) for r in rows]
        sp = [int(r["strategyproof"]) / k for r, k in zip(rows, n, strict=True)]
        cond = [int(r["thm54_walk"]) / k for r, k in zip(rows, n, strict=True)]
        ax.plot(ps, sp, style, marker="o", color="#1f77b4", label=f"strategyproof ({label})")
        ax.plot(ps, cond, style, marker="s", color="#ff7f0e", label=f"Thm 5.4 holds ({label})")
    ax.set_xlabel("attack probability $p$")
    ax.set_ylabel("fraction of instances")
    ax.set_ylim(0, 1.02)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / f"strategyproofness.{fmt}")
    plt.close(fig)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--format", choices=["svg", "pdf", "png"], default="svg")
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "figures")
    parser.add_argument("--no-titles", action="store_true", help="omit titles (for captions)")
    parser.add_argument("--plots", action="store_true", help="also plot experiment results")
    opts = parser.parse_args(argv)

    opts.out.mkdir(parents=True, exist_ok=True)
    render_examples(opts.out, opts.format, titles=not opts.no_titles)
    if opts.plots:
        plot_results(opts.out, opts.format)
    print(f"wrote figures to {opts.out}")


if __name__ == "__main__":
    main()
