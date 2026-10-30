"""Acceptance status of individual arguments (Def 5.8)."""

from __future__ import annotations

from enum import Enum

from argumentation.framework import Argument, ArgumentationFramework
from argumentation.semantics import extensions


class Status(str, Enum):
    SKEPTICALLY_ACCEPTED = "skeptically accepted"
    CREDULOUSLY_ACCEPTED = "credulously accepted"
    REJECTED = "rejected"

    def __str__(self) -> str:
        return self.value


def acceptance_status(
    af: ArgumentationFramework, argument: Argument, semantics: str = "preferred"
) -> Status:
    """Classify ``argument`` against the extensions of ``semantics``.

    Skeptical acceptance implies credulous acceptance, so the strongest status
    that holds is returned. When the semantics yields no extensions at all
    (possible for stable), the argument is rejected: Def 5.8 would otherwise
    make it vacuously skeptically accepted yet not credulously accepted.
    """
    if argument not in af:
        raise KeyError(f"unknown argument: {argument!r}")
    exts = extensions(af, semantics)
    containing = sum(argument in e for e in exts)
    if exts and containing == len(exts):
        return Status.SKEPTICALLY_ACCEPTED
    if containing:
        return Status.CREDULOUSLY_ACCEPTED
    return Status.REJECTED


def acceptance_report(
    af: ArgumentationFramework, semantics: str = "preferred"
) -> dict[Argument, Status]:
    """Status of every argument in ``af``."""
    return {a: acceptance_status(af, a, semantics) for a in sorted(af.arguments, key=str)}
