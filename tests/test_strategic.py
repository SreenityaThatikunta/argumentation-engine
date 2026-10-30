import random

import pytest

from argumentation.examples import example_5_10, example_5_11
from argumentation.strategic import (
    Game,
    best_responses,
    indirect_defeats,
    is_strategyproof,
    mechanism,
    satisfies_theorem_5_4,
    theorem_5_4_violations,
    utility,
)


def fs(*args):
    return frozenset(args)


class TestMechanism:
    def test_example_5_10_truthful_outcome(self):
        attacks, types = example_5_10()
        assert mechanism(attacks, types) == {"a1", "a3"}

    def test_example_5_10_utilities_with_errata(self):
        # The book swaps y's and z's argument sets; y holds α2, z holds α3.
        attacks, types = example_5_10()
        o = mechanism(attacks, types)
        assert utility(o, types["x"]) == 1
        assert utility(o, types["y"]) == 0
        assert utility(o, types["z"]) == 1

    def test_example_5_10_hiding_a1(self):
        attacks, types = example_5_10()
        o = mechanism(attacks, {**types, "x": {"a4", "a5"}})
        assert o == {"a2", "a4", "a5"}
        assert utility(o, types["x"]) == 2

    def test_only_attacks_between_revealed_arguments_count(self):
        attacks, _ = example_5_10()
        assert mechanism(attacks, {"x": {"a4"}, "z": set()}) == {"a4"}

    def test_example_5_11_truthful_outcome(self):
        attacks, types = example_5_11()
        assert mechanism(attacks, types) == {"a1", "a4", "a5", "a6"}


class TestBestResponses:
    def test_x_hides_a1_against_truthful_others(self):
        attacks, types = example_5_10()
        br = best_responses(attacks, types, "x", {"y": types["y"], "z": types["z"]})
        assert br.utility == 2
        assert br.reports == [fs("a4", "a5")]

    def test_y_and_z_weakly_prefer_truth(self):
        attacks, types = example_5_10()
        for agent in ("y", "z"):
            others = {a: t for a, t in types.items() if a != agent}
            br = best_responses(attacks, types, agent, others)
            assert frozenset(types[agent]) in br.reports

    def test_example_5_11_truth_is_best_for_x(self):
        attacks, types = example_5_11()
        br = best_responses(attacks, types, "x", {"y": types["y"], "z": types["z"]})
        assert br.utility == 4
        assert br.reports == [fs("a1", "a4", "a5", "a6")]


class TestTheorem53:
    def test_example_5_10_not_strategyproof(self):
        attacks, types = example_5_10()
        assert not is_strategyproof(attacks, types)

    def test_example_5_10_manipulation_witness(self):
        attacks, types = example_5_10()
        found = list(Game(attacks, types).manipulations())
        assert {m.agent for m in found} == {"x"}
        assert all(m.hidden == {"a1"} for m in found)

    def test_example_5_11_strategyproof(self):
        attacks, types = example_5_11()
        assert is_strategyproof(attacks, types)

    def test_single_agent_without_conflicts(self):
        assert is_strategyproof({("a", "b")}, {"x": {"a"}, "y": {"b"}})


class TestIndirectDefeats:
    def test_chain_parities(self):
        attacks = {("a", "b"), ("b", "c"), ("c", "d")}
        defeats = indirect_defeats(attacks, "abcd")
        assert ("a", "b") in defeats and ("a", "d") in defeats
        assert ("a", "c") not in defeats

    def test_cycles_terminate_and_flip_parity_for_walks(self):
        # a ⇀ b ⇀ c ⇀ a: every pair is reachable at both parities by walks.
        attacks = {("a", "b"), ("b", "c"), ("c", "a")}
        assert indirect_defeats(attacks, "abc", "walk") == {(x, y) for x in "abc" for y in "abc"}

    def test_simple_paths_on_odd_cycle(self):
        attacks = {("a", "b"), ("b", "c"), ("c", "a")}
        simple = indirect_defeats(attacks, "abc", "simple")
        assert ("a", "b") in simple and ("a", "a") in simple
        assert ("a", "c") not in simple  # only simple path a→b→c has length 2

    def test_walk_and_simple_differ(self):
        # g ⇀ u, 3-cycle u ⇀ v ⇀ w ⇀ u, u ⇀ t: only g→u→t (even) is simple,
        # but g→u→v→w→u→t has length 5.
        attacks = {("g", "u"), ("u", "v"), ("v", "w"), ("w", "u"), ("u", "t")}
        assert ("g", "t") in indirect_defeats(attacks, "guvwt", "walk")
        assert ("g", "t") not in indirect_defeats(attacks, "guvwt", "simple")

    def test_walks_include_all_simple_paths(self):
        rng = random.Random(1)
        for _ in range(30):
            args = [f"a{i}" for i in range(6)]
            attacks = {(a, b) for a in args for b in args if rng.random() < 0.3}
            assert indirect_defeats(attacks, args, "simple") <= indirect_defeats(
                attacks, args, "walk"
            )

    def test_unknown_mode(self):
        with pytest.raises(ValueError):
            indirect_defeats(set(), "a", "trail")


class TestTheorem54:
    @pytest.mark.parametrize("paths", ["walk", "simple"])
    def test_example_5_10_fails_condition(self, paths):
        attacks, types = example_5_10()
        violations = theorem_5_4_violations(attacks, types, paths)
        assert ("x", "a1", "a4") in violations
        assert ("x", "a1", "a5") in violations
        assert not satisfies_theorem_5_4(attacks, types, paths)

    @pytest.mark.parametrize("paths", ["walk", "simple"])
    def test_example_5_11_fails_condition_yet_strategyproof(self, paths):
        attacks, types = example_5_11()
        assert not satisfies_theorem_5_4(attacks, types, paths)
        assert is_strategyproof(attacks, types)

    def test_self_attack_violates(self):
        assert not satisfies_theorem_5_4({("a", "a")}, {"x": {"a"}})

    def test_condition_holds(self):
        attacks = {("a", "b"), ("b", "c")}
        assert satisfies_theorem_5_4(attacks, {"x": {"a", "c"}, "y": {"b"}})


@pytest.mark.parametrize("seed", range(40))
def test_condition_implies_strategyproof_on_random_instances(seed):
    """Theorem 5.4 under the walk interpretation, checked by brute force."""
    rng = random.Random(seed)
    args = [f"a{i}" for i in range(rng.randint(3, 6))]
    attacks = {(a, b) for a in args for b in args if a != b and rng.random() < 0.25}
    types = {agent: set() for agent in "xyz"}
    for a in args:
        types[rng.choice("xyz")].add(a)
    if satisfies_theorem_5_4(attacks, types, "walk"):
        assert is_strategyproof(attacks, types)
