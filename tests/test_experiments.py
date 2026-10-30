import random

from argumentation.examples import example_5_10, example_5_11
from argumentation.strategic import Game, theorem_5_4_violations
from experiments.run_experiments import evaluate, explain_strategyproof, generate_instance


def test_generated_instance_shape():
    rng = random.Random(0)
    for _ in range(50):
        args, attacks, types = generate_instance(rng, 0.3, range(6, 9), self_attacks=False)
        assert 6 <= len(args) <= 8
        assert sorted(a for t in types.values() for a in t) == sorted(args)
        assert all(a != b for a, b in attacks)


def test_example_5_11_is_explained_as_never_rescues():
    attacks, types = example_5_11()
    game = Game(attacks, types)
    assert explain_strategyproof(game, theorem_5_4_violations(attacks, types)) == "never_rescues"


def test_direct_own_conflict_is_a_costly_rescue():
    # Hiding a5 rescues a1 but loses a5 itself.
    attacks = {("a5", "a1")}
    types = {"x": {"a1", "a5"}, "y": set(), "z": set()}
    game = Game(attacks, types)
    assert game.is_strategyproof()
    assert explain_strategyproof(game, theorem_5_4_violations(attacks, types)) == "rescue_costs_as_much"


def test_evaluate_records_manipulation():
    attacks, types = example_5_10()
    record = evaluate(0, 0.0, ["a1", "a2", "a3", "a4", "a5"], sorted(attacks),
                      {k: sorted(v) for k, v in types.items()})
    assert not record["strategyproof"]
    assert record["manipulation"]["agent"] == "x"
    assert not record["thm54_walk"] and not record["thm54_simple"]
