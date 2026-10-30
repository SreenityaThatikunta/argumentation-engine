"""Graphviz rendering of argumentation frameworks and mechanism outcomes.

Builds DOT source directly, so there is no Python dependency; ``render``
needs the Graphviz ``dot`` executable on PATH.

Colours follow labellings: ``in`` green, ``out`` red, ``undec`` grey.
Arguments an agent did not reveal are drawn dashed and unlabelled.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterable, Mapping
from pathlib import Path

from argumentation.framework import Argument, ArgumentationFramework, Attack
from argumentation.labelling import Label, extension_to_labelling
from argumentation.strategic import Agent, Profile, induced_framework, mechanism

FILL = {Label.IN: "#66bb6a", Label.OUT: "#ef5350", Label.UNDEC: "#bdbdbd"}
MUTED = "#9e9e9e"
SHAPES = ("circle", "box", "diamond", "hexagon", "octagon", "triangle")


def to_dot(
    af: ArgumentationFramework,
    labelling: Mapping[Argument, Label] | None = None,
    owners: Profile | None = None,
    hidden: Iterable[Argument] = (),
    hidden_attacks: Iterable[Attack] = (),
    title: str | None = None,
) -> str:
    """DOT source for ``af``.

    ``owners`` gives each agent's arguments; agents get distinct node shapes
    and their name is shown under each argument. ``hidden`` arguments and
    ``hidden_attacks`` are drawn dashed (used to show withheld arguments).
    """
    hidden = frozenset(hidden)
    owner_of: dict[Argument, Agent] = {}
    shape_of: dict[Agent, str] = {}
    for i, (agent, args) in enumerate((owners or {}).items()):
        shape_of[agent] = SHAPES[i % len(SHAPES)]
        owner_of.update(dict.fromkeys(args, agent))

    lines = [
        "digraph AF {",
        '  graph [rankdir=LR, bgcolor="transparent", pad=0.3, nodesep=0.5, ranksep=0.7,',
        f'         fontname="Helvetica", fontcolor="{MUTED}", labelloc=t];',
        '  node [fontname="Helvetica", style=filled, fillcolor="white", width=0.6];',
        f'  edge [color="{MUTED}", arrowsize=0.8];',
    ]
    if title:
        lines.append(f"  label={_quote(title)};")

    for a in sorted(af.arguments | hidden, key=str):
        attrs = {"label": str(a), "shape": "circle"}
        if a in owner_of:
            agent = owner_of[a]
            attrs["label"] = f"{a}\n({agent})"
            attrs["shape"] = shape_of[agent]
        if a in hidden:
            attrs.update(style="dashed", color=MUTED, fontcolor=MUTED)
        elif labelling is not None and a in labelling:
            attrs["fillcolor"] = FILL[labelling[a]]
        lines.append(f"  {_quote(a)} [{_attrs(attrs)}];")

    for a, b in sorted(af.attacks, key=lambda e: (str(e[0]), str(e[1]))):
        lines.append(f"  {_quote(a)} -> {_quote(b)};")
    for a, b in sorted(hidden_attacks, key=lambda e: (str(e[0]), str(e[1]))):
        lines.append(f"  {_quote(a)} -> {_quote(b)} [style=dashed];")

    lines.append("}")
    return "\n".join(lines) + "\n"


def mechanism_dot(
    attacks: Iterable[Attack],
    types: Profile,
    reports: Profile,
    title: str | None = None,
) -> str:
    """The graph induced by ``reports``, labelled by its grounded extension.

    Arguments in ``types`` that were not reported are shown dashed.
    """
    attacks = frozenset(attacks)
    everything = frozenset().union(*map(frozenset, types.values()))
    revealed = frozenset().union(*map(frozenset, reports.values()))
    af = induced_framework(attacks, revealed)
    labelling = extension_to_labelling(af, mechanism(attacks, reports))
    hidden = everything - revealed
    hidden_attacks = {(a, b) for a, b in attacks if a in hidden or b in hidden}
    return to_dot(af, labelling, types, hidden, hidden_attacks, title)


def render(dot_source: str, path: str | Path) -> Path:
    """Render DOT source to ``path``; the format comes from its suffix (.svg, .png, .pdf)."""
    dot = shutil.which("dot")
    if dot is None:
        raise RuntimeError("Graphviz 'dot' executable not found; install Graphviz to render")
    path = Path(path)
    fmt = path.suffix.lstrip(".") or "svg"
    subprocess.run([dot, f"-T{fmt}", "-o", str(path)], input=dot_source, text=True, check=True)
    return path


def _quote(value: object) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def _attrs(attrs: Mapping[str, object]) -> str:
    return ", ".join(f"{k}={_quote(v)}" for k, v in attrs.items())
