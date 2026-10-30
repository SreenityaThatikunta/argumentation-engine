"""Render the textbook examples to docs/figures/ (requires Graphviz).

Usage:
    python experiments/figures.py
"""

from __future__ import annotations

from pathlib import Path

from argumentation.examples import example_5_10, example_5_11, figure_5_1, figure_5_2
from argumentation.labelling import grounded_labelling, legal_labellings
from argumentation.visualize import mechanism_dot, render, to_dot

OUT = Path(__file__).resolve().parent.parent / "docs" / "figures"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    af = figure_5_1()
    render(
        to_dot(af, grounded_labelling(af), title="Figure 5.1: grounded labelling"),
        OUT / "figure_5_1.svg",
    )

    af = figure_5_2()
    for i, lab in enumerate(legal_labellings(af), 1):
        title = f"Figure 5.2: complete labelling {i} of 3"
        render(to_dot(af, lab, title=title), OUT / f"figure_5_2_labelling_{i}.svg")

    attacks, types = example_5_10()
    render(
        mechanism_dot(attacks, types, types, "Example 5.10: all agents truthful (x gets 1)"),
        OUT / "example_5_10_truthful.svg",
    )
    hiding = {**types, "x": types["x"] - {"a1"}}
    render(
        mechanism_dot(attacks, types, hiding, "Example 5.10: x hides a1 (x gets 2)"),
        OUT / "example_5_10_x_hides_a1.svg",
    )

    attacks, types = example_5_11()
    render(
        mechanism_dot(attacks, types, types, "Example 5.11: a6 cancels the self-defeat (x gets 4)"),
        OUT / "example_5_11_truthful.svg",
    )
    print(f"wrote figures to {OUT}")


if __name__ == "__main__":
    main()
