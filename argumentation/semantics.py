"""Extension-based semantics (Def 5.7).

Every function takes an ``ArgumentationFramework`` and returns extensions as
frozensets. Functions returning several extensions sort them by size and then
by their sorted members, so results are deterministic.
"""

from __future__ import annotations

from collections.abc import Callable

from argumentation.framework import Argument, ArgumentationFramework

Extension = frozenset[Argument]


def grounded(af: ArgumentationFramework) -> Extension:
    """The least fixed point of F, reached by iterating F from ∅."""
    s: Extension = frozenset()
    while (nxt := af.characteristic(s)) != s:
        s = nxt
    return s


def complete_extensions(af: ArgumentationFramework) -> list[Extension]:
    """Every conflict-free S with S = F(S).

    Every complete extension contains the grounded extension G and excludes
    G⁺, so the search only branches over the remaining arguments, extending
    conflict-free sets one argument at a time.
    """
    g = grounded(af)
    undecided = sorted(af.arguments - g - af.plus(g), key=str)
    found: list[Extension] = []

    def extend(i: int, s: Extension) -> None:
        if i == len(undecided):
            if af.is_complete(s):
                found.append(s)
            return
        extend(i + 1, s)
        candidate = s | {undecided[i]}
        if af.is_conflict_free(candidate):
            extend(i + 1, candidate)

    extend(0, g)
    return _sorted(found)


def preferred_extensions(af: ArgumentationFramework) -> list[Extension]:
    """The ⊆-maximal complete extensions."""
    return _maximal(complete_extensions(af), key=lambda s: s)


def stable_extensions(af: ArgumentationFramework) -> list[Extension]:
    """Complete extensions that attack every argument outside them (S⁺ = A \\ S).

    May be empty.
    """
    return [s for s in complete_extensions(af) if af.plus(s) == af.arguments - s]


def semi_stable_extensions(af: ArgumentationFramework) -> list[Extension]:
    """Complete extensions whose range S ∪ S⁺ is ⊆-maximal."""
    return _maximal(complete_extensions(af), key=lambda s: s | af.plus(s))


SEMANTICS: dict[str, Callable[[ArgumentationFramework], list[Extension]]] = {
    "grounded": lambda af: [grounded(af)],
    "complete": complete_extensions,
    "preferred": preferred_extensions,
    "stable": stable_extensions,
    "semi-stable": semi_stable_extensions,
}


def extensions(af: ArgumentationFramework, semantics: str) -> list[Extension]:
    """Extensions of ``af`` under a semantics named in ``SEMANTICS``."""
    try:
        return SEMANTICS[semantics](af)
    except KeyError:
        raise ValueError(f"unknown semantics {semantics!r}; choose from {sorted(SEMANTICS)}") from None


def _maximal(
    candidates: list[Extension], key: Callable[[Extension], frozenset]
) -> list[Extension]:
    keys = [key(c) for c in candidates]
    return _sorted(
        c for c, k in zip(candidates, keys) if not any(k < other for other in keys)
    )


def _sorted(exts) -> list[Extension]:
    return sorted(exts, key=lambda s: (len(s), sorted(map(str, s))))
