"""Strategic argumentation with the grounded direct mechanism (Sections 5.3-5.4).

Each agent holds a private set of arguments (its type) and reports a subset
of it; agents may hide arguments but never invent them. The mechanism accepts
the grounded extension of the graph induced by the union of all reports, and
an agent's utility is the number of its own arguments that are accepted.

Agents are identified by any hashable key; ``types`` and ``reports`` map each
agent to a set of arguments. ``attacks`` is the global defeat relation over
all arguments.
"""

from __future__ import annotations

from collections.abc import Hashable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from functools import lru_cache
from itertools import chain, combinations, product

from argumentation.framework import Argument, Attack, ArgumentationFramework
from argumentation.semantics import Extension, grounded

Agent = Hashable
Profile = Mapping[Agent, Iterable[Argument]]


def induced_framework(attacks: Iterable[Attack], arguments: Iterable[Argument]) -> ArgumentationFramework:
    """The subgraph on ``arguments``: only attacks between them survive."""
    arguments = frozenset(arguments)
    return ArgumentationFramework(
        arguments, ((a, b) for a, b in attacks if a in arguments and b in arguments)
    )


def mechanism(attacks: Iterable[Attack], reports: Profile) -> Extension:
    """Grounded extension of the graph induced by the union of all reports (Def 5.21)."""
    revealed = frozenset().union(*map(frozenset, reports.values()))
    return grounded(induced_framework(attacks, revealed))


def utility(outcome: Iterable[Argument], own_arguments: Iterable[Argument]) -> int:
    """Acceptability-maximising utility |o ∩ Aᵢ| (Def 5.22)."""
    return len(frozenset(outcome) & frozenset(own_arguments))


@dataclass(frozen=True)
class BestResponses:
    utility: int
    reports: list[frozenset[Argument]]


@dataclass(frozen=True)
class Manipulation:
    """A situation in which ``agent`` gains by not revealing its whole type."""

    agent: Agent
    others: dict[Agent, frozenset[Argument]]
    report: frozenset[Argument]
    hidden: frozenset[Argument]
    truthful_utility: int
    manipulated_utility: int


def subsets(arguments: Iterable[Argument]) -> Iterator[frozenset[Argument]]:
    """Every subset of ``arguments``, smallest first."""
    items = sorted(arguments, key=str)
    return (
        frozenset(c)
        for c in chain.from_iterable(combinations(items, r) for r in range(len(items) + 1))
    )


class Game:
    """A grounded direct argumentation mechanism instance.

    Grounded extensions are cached by the set of revealed arguments, since
    many report profiles reveal the same union.
    """

    def __init__(self, attacks: Iterable[Attack], types: Profile):
        self.attacks = frozenset(attacks)
        self.types = {agent: frozenset(args) for agent, args in types.items()}
        self.arguments = frozenset().union(*self.types.values())
        self._outcome = lru_cache(maxsize=None)(self._grounded_of)

    def _grounded_of(self, revealed: frozenset[Argument]) -> Extension:
        return grounded(induced_framework(self.attacks, revealed))

    def outcome(self, reports: Profile) -> Extension:
        return self._outcome(frozenset().union(*map(frozenset, reports.values())))

    def utility(self, agent: Agent, reports: Profile) -> int:
        return utility(self.outcome(reports), self.types[agent])

    def best_responses(self, agent: Agent, others: Profile) -> BestResponses:
        """The reports ⊆ Aᵢ maximising the agent's utility, others held fixed."""
        others = {a: frozenset(r) for a, r in others.items() if a != agent}
        scored = [
            (self.utility(agent, {**others, agent: report}), report)
            for report in subsets(self.types[agent])
        ]
        best = max(u for u, _ in scored)
        return BestResponses(best, [r for u, r in scored if u == best])

    def manipulations(self, agent: Agent | None = None) -> Iterator[Manipulation]:
        """Every (others' reports, better report) pair beating truthful revelation."""
        agents = [agent] if agent is not None else list(self.types)
        for i in agents:
            truth = self.types[i]
            others = [a for a in self.types if a != i]
            for combo in product(*(list(subsets(self.types[a])) for a in others)):
                fixed = dict(zip(others, combo))
                truthful = self.utility(i, {**fixed, i: truth})
                for report in subsets(truth):
                    gained = self.utility(i, {**fixed, i: report})
                    if gained > truthful:
                        yield Manipulation(i, fixed, report, truth - report, truthful, gained)

    def is_strategyproof(self) -> bool:
        """Theorem 5.3: for every agent and every combination of subsets the
        others could reveal, revealing all of Aᵢ is a best response."""
        return next(self.manipulations(), None) is None


def best_responses(
    attacks: Iterable[Attack], types: Profile, agent: Agent, others: Profile
) -> BestResponses:
    """Best responses of ``agent`` given fixed reports by the other agents."""
    return Game(attacks, types).best_responses(agent, others)


def is_strategyproof(attacks: Iterable[Attack], types: Profile) -> bool:
    """Exhaustive strategyproofness check (Theorem 5.3)."""
    return Game(attacks, types).is_strategyproof()


def indirect_defeats(
    attacks: Iterable[Attack], arguments: Iterable[Argument], paths: str = "walk"
) -> frozenset[Attack]:
    """Pairs (α, β) with an odd-length directed path from α to β (α ↪ β).

    ``paths="walk"`` lets a path revisit arguments. Cycles are handled by a
    search over (argument, parity) states, so each state is visited once.

    ``paths="simple"`` only counts paths that visit each argument at most
    once (a cycle back to α itself counts for the pair (α, α)). This
    enumerates paths and is exponential, but fine for small graphs.
    """
    arguments = frozenset(arguments)
    successors: dict[Argument, list[Argument]] = {a: [] for a in arguments}
    for a, b in attacks:
        if a in arguments and b in arguments:
            successors[a].append(b)

    if paths == "walk":
        return frozenset(
            (src, dst) for src in arguments for dst in _odd_walk_targets(src, successors)
        )
    if paths == "simple":
        return frozenset(
            (src, dst) for src in arguments for dst in _odd_simple_path_targets(src, successors)
        )
    raise ValueError(f"paths must be 'walk' or 'simple', not {paths!r}")


def _odd_walk_targets(src, successors) -> set:
    seen = {(src, 0)}
    stack = [(src, 0)]
    while stack:
        node, parity = stack.pop()
        for nxt in successors[node]:
            state = (nxt, parity ^ 1)
            if state not in seen:
                seen.add(state)
                stack.append(state)
    return {node for node, parity in seen if parity == 1}


def _odd_simple_path_targets(src, successors) -> set:
    found = set()

    def visit(node, length, on_path):
        for nxt in successors[node]:
            if nxt == src:
                if (length + 1) % 2:
                    found.add(src)
            elif nxt not in on_path:
                if (length + 1) % 2:
                    found.add(nxt)
                visit(nxt, length + 1, on_path | {nxt})

    visit(src, 0, frozenset({src}))
    return found


def theorem_5_4_violations(
    attacks: Iterable[Attack], types: Profile, paths: str = "walk"
) -> list[tuple[Agent, Argument, Argument]]:
    """Every (agent, α, β) with α, β ∈ Aᵢ and α ↪ β in the full graph.

    α = β is included, matching the theorem's formal statement; a direct
    self-attack is the length-1 case, so this also covers conflict-freeness.
    """
    types = {agent: frozenset(args) for agent, args in types.items()}
    defeats = indirect_defeats(attacks, frozenset().union(*types.values()), paths)
    return sorted(
        ((agent, a, b) for agent, own in types.items() for a, b in defeats if a in own and b in own),
        key=lambda t: tuple(map(str, t)),
    )


def satisfies_theorem_5_4(attacks: Iterable[Attack], types: Profile, paths: str = "walk") -> bool:
    """Sufficient condition for strategyproofness (Theorem 5.4): no agent holds
    α, β with an odd-length path from α to β in the full graph."""
    return not theorem_5_4_violations(attacks, types, paths)
