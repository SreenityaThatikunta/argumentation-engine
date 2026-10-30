"""Cross-check the bitmask engine in experiments/exhaustive.py against the library."""

import random

import pytest

from argumentation import ArgumentationFramework, grounded
from argumentation.strategic import Game, indirect_defeats, satisfies_theorem_5_4
from experiments.exhaustive import (
    check_range,
    condition_holds,
    decode,
    edge_list,
    manipulation,
    odd_simple_reach,
    odd_walk_reach,
)
from experiments.exhaustive import grounded as grounded_mask


def random_graph(rng, n, self_attacks=True):
    edges = edge_list(n, self_attacks)
    graph = rng.getrandbits(len(edges))
    attackers, successors = decode(n, edges, graph)
    attacks = {e for i, e in enumerate(edges) if graph >> i & 1}
    return attackers, successors, attacks


def mask_to_set(mask):
    return {i for i in range(mask.bit_length()) if mask >> i & 1}


@pytest.mark.parametrize("seed", range(40))
def test_bitmask_engine_matches_library(seed):
    rng = random.Random(seed)
    n = rng.randint(1, 6)
    attackers, successors, attacks = random_graph(rng, n)
    full = (1 << n) - 1
    args = range(n)

    revealed = rng.getrandbits(n)
    sub = ArgumentationFramework(
        mask_to_set(revealed),
        {(a, b) for a, b in attacks if revealed >> a & 1 and revealed >> b & 1},
    )
    assert mask_to_set(grounded_mask(attackers, revealed)) == grounded(sub)

    for mode, reach in (("walk", odd_walk_reach), ("simple", odd_simple_reach)):
        defeats = indirect_defeats(attacks, args, mode)
        for src in args:
            assert mask_to_set(reach(successors, src)) == {b for a, b in defeats if a == src}

    own = rng.getrandbits(n)
    types = {"x": mask_to_set(own), "rest": mask_to_set(full & ~own)}
    outcomes = [grounded_mask(attackers, r) for r in range(full + 1)]
    game = Game(attacks, types)
    expected_manipulable = next(game.manipulations("x"), None) is not None
    assert (manipulation(outcomes, own, full) is not None) == expected_manipulable
    assert condition_holds(successors, own, odd_walk_reach) == satisfies_theorem_5_4(
        attacks, {"x": types["x"]}, "walk"
    )


def test_example_5_10_relabelled():
    # α1..α5 -> 0..4; agent x owns {α1, α4, α5}.
    attacks = [(0, 1), (1, 2), (2, 3), (2, 4)]
    attackers = [0] * 5
    successors = [0] * 5
    for a, b in attacks:
        attackers[b] |= 1 << a
        successors[a] |= 1 << b
    own = 0b11001
    outcomes = [grounded_mask(attackers, r) for r in range(32)]
    others, report = manipulation(outcomes, own, 31)
    manipulated = (outcomes[report | others] & own).bit_count()
    truthful = (outcomes[own | others] & own).bit_count()
    assert manipulated > truthful
    assert not condition_holds(successors, own, odd_walk_reach)


def test_check_range_counts_small_n():
    tallies = check_range((2, False, 0, 4))
    assert sum(t.pairs for t in tallies.values()) == 4 * 3
    assert all(t.q2_walk == 0 for t in tallies.values())
