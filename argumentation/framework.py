"""Dung-style abstract argumentation frameworks.

Implements Definitions 5.1-5.5 of Rahwan, "Argumentation among Agents"
(Weiss, Multiagent Systems, 2nd ed., Chapter 5).
"""

from __future__ import annotations

from collections.abc import Hashable, Iterable

Argument = Hashable
Attack = tuple[Argument, Argument]


class ArgumentationFramework:
    """An argumentation framework <A, ⇀> (Def 5.1).

    ``arguments`` is a finite set of hashable labels and ``attacks`` a set of
    ``(attacker, target)`` pairs over those labels.
    """

    def __init__(self, arguments: Iterable[Argument], attacks: Iterable[Attack] = ()):
        self._arguments = frozenset(arguments)
        self._attacks = frozenset((a, b) for a, b in attacks)

        unknown = {x for pair in self._attacks for x in pair} - self._arguments
        if unknown:
            raise ValueError(f"attacks mention unknown arguments: {sorted(map(str, unknown))}")

        attackers: dict[Argument, set[Argument]] = {a: set() for a in self._arguments}
        targets: dict[Argument, set[Argument]] = {a: set() for a in self._arguments}
        for a, b in self._attacks:
            attackers[b].add(a)
            targets[a].add(b)
        self._attackers = {a: frozenset(s) for a, s in attackers.items()}
        self._targets = {a: frozenset(s) for a, s in targets.items()}

    @property
    def arguments(self) -> frozenset[Argument]:
        return self._arguments

    @property
    def attacks(self) -> frozenset[Attack]:
        return self._attacks

    def attackers(self, argument: Argument) -> frozenset[Argument]:
        """α⁻: the arguments that attack ``argument``."""
        return self._attackers[self._check_argument(argument)]

    def attacked_by(self, argument: Argument) -> frozenset[Argument]:
        """The arguments that ``argument`` attacks."""
        return self._targets[self._check_argument(argument)]

    def plus(self, s: Iterable[Argument]) -> frozenset[Argument]:
        """S⁺: every argument attacked by some member of S."""
        return frozenset().union(*(self._targets[a] for a in self._check_set(s)))

    def is_conflict_free(self, s: Iterable[Argument]) -> bool:
        """S ∩ S⁺ = ∅ (Def 5.2)."""
        s = self._check_set(s)
        return s.isdisjoint(self.plus(s))

    def defends(self, s: Iterable[Argument], argument: Argument) -> bool:
        """α⁻ ⊆ S⁺: S attacks every attacker of ``argument`` (Def 5.2)."""
        return self.attackers(argument) <= self.plus(s)

    def characteristic(self, s: Iterable[Argument]) -> frozenset[Argument]:
        """F(S): the set of arguments defended by S (Def 5.3)."""
        s_plus = self.plus(s)
        return frozenset(a for a in self._arguments if self._attackers[a] <= s_plus)

    def is_admissible(self, s: Iterable[Argument]) -> bool:
        """Conflict-free and S ⊆ F(S) (Def 5.4)."""
        s = self._check_set(s)
        return self.is_conflict_free(s) and s <= self.characteristic(s)

    def is_complete(self, s: Iterable[Argument]) -> bool:
        """Conflict-free and S = F(S) (Def 5.5)."""
        s = self._check_set(s)
        return self.is_conflict_free(s) and s == self.characteristic(s)

    def _check_argument(self, argument: Argument) -> Argument:
        if argument not in self._arguments:
            raise KeyError(f"unknown argument: {argument!r}")
        return argument

    def _check_set(self, s: Iterable[Argument]) -> frozenset[Argument]:
        s = frozenset(s)
        unknown = s - self._arguments
        if unknown:
            raise KeyError(f"unknown arguments: {sorted(map(str, unknown))}")
        return s

    def __len__(self) -> int:
        return len(self._arguments)

    def __contains__(self, argument: object) -> bool:
        return argument in self._arguments

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ArgumentationFramework):
            return NotImplemented
        return self._arguments == other._arguments and self._attacks == other._attacks

    def __hash__(self) -> int:
        return hash((self._arguments, self._attacks))

    def __repr__(self) -> str:
        args = ", ".join(sorted(map(str, self._arguments)))
        atts = ", ".join(sorted(f"{a}->{b}" for a, b in self._attacks))
        return f"ArgumentationFramework(arguments={{{args}}}, attacks={{{atts}}})"
