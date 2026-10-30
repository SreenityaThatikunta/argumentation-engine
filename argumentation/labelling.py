"""Argument labellings (Def 5.6, Table 5.1).

A labelling maps every argument to ``in``, ``out`` or ``undec``. It is legal
when an argument is ``in`` iff all its attackers are ``out``, and ``out`` iff
some attacker is ``in``. Legal labellings correspond one-to-one with complete
extensions: in(L) is the extension and out(L) is its S⁺.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import Enum

from argumentation.framework import Argument, ArgumentationFramework
from argumentation.semantics import Extension, complete_extensions, grounded


class Label(str, Enum):
    IN = "in"
    OUT = "out"
    UNDEC = "undec"

    def __str__(self) -> str:
        return self.value


Labelling = dict[Argument, Label]


def extension_to_labelling(af: ArgumentationFramework, s: Iterable[Argument]) -> Labelling:
    """Label S as ``in``, S⁺ as ``out`` and everything else ``undec``."""
    s = frozenset(s)
    s_plus = af.plus(s)
    return {
        a: Label.IN if a in s else Label.OUT if a in s_plus else Label.UNDEC for a in af.arguments
    }


def labelling_to_extension(labelling: Mapping[Argument, Label]) -> Extension:
    """in(L): the arguments labelled ``in``."""
    return frozenset(a for a, label in labelling.items() if label is Label.IN)


def is_legal_labelling(af: ArgumentationFramework, labelling: Mapping[Argument, Label]) -> bool:
    """Check the in/out/undec conditions of Def 5.6 for every argument."""
    if set(labelling) != af.arguments:
        return False
    for a in af.arguments:
        attacker_labels = {labelling[b] for b in af.attackers(a)}
        should_be_out = Label.IN in attacker_labels
        should_be_in = attacker_labels <= {Label.OUT}
        if (labelling[a] is Label.OUT) != should_be_out:
            return False
        if (labelling[a] is Label.IN) != should_be_in:
            return False
    return True


def legal_labellings(af: ArgumentationFramework) -> list[Labelling]:
    """Every legal labelling, one per complete extension."""
    return [extension_to_labelling(af, s) for s in complete_extensions(af)]


def grounded_labelling(af: ArgumentationFramework) -> Labelling:
    """The labelling with minimal ``in`` (maximal ``undec``)."""
    return extension_to_labelling(af, grounded(af))
