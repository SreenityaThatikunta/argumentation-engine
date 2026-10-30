import random
from itertools import combinations

import pytest

from argumentation import ArgumentationFramework
from argumentation.examples import figure_5_1, figure_5_2
from argumentation.semantics import (
    complete_extensions,
    extensions,
    grounded,
    preferred_extensions,
    semi_stable_extensions,
    stable_extensions,
)


def fs(*args):
    return frozenset(args)


@pytest.fixture
def three_cycle():
    return ArgumentationFramework(["a", "b", "c"], [("a", "b"), ("b", "c"), ("c", "a")])


@pytest.fixture
def semi_stable_differs():
    """a ⇄ b, b ⇀ c, c ⇀ c, plus an isolated 3-cycle x ⇀ y ⇀ z ⇀ x.

    No stable extension exists, both {a} and {b} are preferred, but only {b}
    has a maximal range.
    """
    return ArgumentationFramework(
        ["a", "b", "c", "x", "y", "z"],
        [("a", "b"), ("b", "a"), ("b", "c"), ("c", "c"), ("x", "y"), ("y", "z"), ("z", "x")],
    )


class TestFigure51:
    def test_grounded(self):
        assert grounded(figure_5_1()) == {"a1", "a3", "a5"}

    def test_single_extension_under_every_semantics(self):
        expected = [fs("a1", "a3", "a5")]
        af = figure_5_1()
        assert complete_extensions(af) == expected
        assert preferred_extensions(af) == expected
        assert stable_extensions(af) == expected
        assert semi_stable_extensions(af) == expected


class TestFigure52:
    def test_grounded(self):
        assert grounded(figure_5_2()) == {"a3"}

    def test_example_5_7_complete(self):
        assert complete_extensions(figure_5_2()) == [
            fs("a3"),
            fs("a1", "a3"),
            fs("a2", "a3"),
        ]

    def test_example_5_8_preferred(self):
        assert preferred_extensions(figure_5_2()) == [fs("a1", "a3"), fs("a2", "a3")]

    def test_stable_and_semi_stable_match_preferred(self):
        af = figure_5_2()
        assert stable_extensions(af) == preferred_extensions(af)
        assert semi_stable_extensions(af) == preferred_extensions(af)


class TestOddCycle:
    def test_only_empty_extension(self, three_cycle):
        assert grounded(three_cycle) == set()
        assert complete_extensions(three_cycle) == [fs()]
        assert preferred_extensions(three_cycle) == [fs()]
        assert semi_stable_extensions(three_cycle) == [fs()]

    def test_no_stable_extension(self, three_cycle):
        assert stable_extensions(three_cycle) == []


class TestSemiStable:
    def test_preferred(self, semi_stable_differs):
        assert preferred_extensions(semi_stable_differs) == [fs("a"), fs("b")]

    def test_no_stable(self, semi_stable_differs):
        assert stable_extensions(semi_stable_differs) == []

    def test_semi_stable_picks_maximal_range(self, semi_stable_differs):
        assert semi_stable_extensions(semi_stable_differs) == [fs("b")]


class TestEdgeCases:
    def test_empty_framework(self):
        af = ArgumentationFramework([])
        assert grounded(af) == set()
        assert complete_extensions(af) == [fs()]
        assert stable_extensions(af) == [fs()]

    def test_unattacked_arguments_are_grounded(self):
        af = ArgumentationFramework(["a", "b"])
        assert grounded(af) == {"a", "b"}

    def test_self_attacker_is_never_accepted(self):
        af = ArgumentationFramework(["a", "b"], [("a", "a"), ("a", "b")])
        assert grounded(af) == set()
        assert complete_extensions(af) == [fs()]

    def test_grounded_is_subset_of_every_complete_extension(self):
        af = figure_5_2()
        g = grounded(af)
        assert all(g <= s for s in complete_extensions(af))


@pytest.mark.parametrize("seed", range(50))
def test_complete_extensions_match_brute_force(seed):
    rng = random.Random(seed)
    args = [f"a{i}" for i in range(rng.randint(1, 7))]
    attacks = [(a, b) for a in args for b in args if rng.random() < 0.3]
    af = ArgumentationFramework(args, attacks)
    every_subset = (frozenset(c) for r in range(len(args) + 1) for c in combinations(args, r))
    expected = {s for s in every_subset if af.is_complete(s)}
    assert set(complete_extensions(af)) == expected
    assert grounded(af) == min(expected, key=len)


class TestDispatch:
    def test_by_name(self):
        assert extensions(figure_5_2(), "grounded") == [fs("a3")]
        assert extensions(figure_5_2(), "preferred") == preferred_extensions(figure_5_2())

    def test_unknown_name(self):
        with pytest.raises(ValueError):
            extensions(figure_5_2(), "ideal")
