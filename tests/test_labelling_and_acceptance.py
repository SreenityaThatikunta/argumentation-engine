import random
from itertools import product

import pytest

from argumentation import ArgumentationFramework
from argumentation.acceptance import Status, acceptance_report, acceptance_status
from argumentation.examples import figure_5_1, figure_5_2
from argumentation.labelling import (
    Label,
    extension_to_labelling,
    grounded_labelling,
    is_legal_labelling,
    labelling_to_extension,
    legal_labellings,
)
from argumentation.semantics import complete_extensions

IN, OUT, UNDEC = Label.IN, Label.OUT, Label.UNDEC


class TestLabellings:
    def test_figure_5_2_has_three_labellings(self):
        # Figure 5.2 shows L1, L2 and the grounded labelling LG.
        assert legal_labellings(figure_5_2()) == [
            {"a1": UNDEC, "a2": UNDEC, "a3": IN},
            {"a1": IN, "a2": OUT, "a3": IN},
            {"a1": OUT, "a2": IN, "a3": IN},
        ]

    def test_grounded_labelling(self):
        assert grounded_labelling(figure_5_1()) == {
            "a1": IN, "a2": OUT, "a3": IN, "a4": OUT, "a5": IN,
        }

    def test_every_generated_labelling_is_legal(self):
        for af in (figure_5_1(), figure_5_2()):
            assert all(is_legal_labelling(af, lab) for lab in legal_labellings(af))

    def test_round_trip_with_complete_extensions(self):
        af = figure_5_2()
        assert [labelling_to_extension(lab) for lab in legal_labellings(af)] == complete_extensions(af)

    def test_illegal_in_with_in_attacker(self):
        assert not is_legal_labelling(figure_5_2(), {"a1": IN, "a2": IN, "a3": IN})

    def test_illegal_undec_with_all_attackers_out(self):
        # a3 is unattacked, so it must be in.
        assert not is_legal_labelling(figure_5_2(), {"a1": UNDEC, "a2": UNDEC, "a3": UNDEC})

    def test_illegal_partial_labelling(self):
        assert not is_legal_labelling(figure_5_2(), {"a1": IN, "a2": OUT})

    def test_extension_to_labelling_marks_attacked_out(self):
        assert extension_to_labelling(figure_5_1(), {"a3"}) == {
            "a1": UNDEC, "a2": OUT, "a3": IN, "a4": UNDEC, "a5": UNDEC,
        }


@pytest.mark.parametrize("seed", range(30))
def test_legal_labellings_match_brute_force(seed):
    rng = random.Random(seed)
    args = [f"a{i}" for i in range(rng.randint(1, 6))]
    attacks = [(a, b) for a in args for b in args if rng.random() < 0.3]
    af = ArgumentationFramework(args, attacks)
    every_labelling = (dict(zip(args, labels)) for labels in product(Label, repeat=len(args)))
    expected = [lab for lab in every_labelling if is_legal_labelling(af, lab)]
    actual = legal_labellings(af)
    assert len(actual) == len(expected)
    assert all(lab in expected for lab in actual)


class TestAcceptance:
    def test_figure_5_2_preferred(self):
        af = figure_5_2()
        assert acceptance_status(af, "a3") is Status.SKEPTICALLY_ACCEPTED
        assert acceptance_status(af, "a1") is Status.CREDULOUSLY_ACCEPTED
        assert acceptance_status(af, "a2") is Status.CREDULOUSLY_ACCEPTED

    def test_figure_5_2_grounded(self):
        af = figure_5_2()
        assert acceptance_status(af, "a1", "grounded") is Status.REJECTED
        assert acceptance_status(af, "a3", "grounded") is Status.SKEPTICALLY_ACCEPTED

    def test_figure_5_1_report(self):
        assert acceptance_report(figure_5_1()) == {
            "a1": Status.SKEPTICALLY_ACCEPTED,
            "a2": Status.REJECTED,
            "a3": Status.SKEPTICALLY_ACCEPTED,
            "a4": Status.REJECTED,
            "a5": Status.SKEPTICALLY_ACCEPTED,
        }

    def test_no_stable_extension_means_rejected(self):
        af = ArgumentationFramework(["a", "b", "c"], [("a", "b"), ("b", "c"), ("c", "a")])
        assert acceptance_status(af, "a", "stable") is Status.REJECTED

    def test_unknown_argument(self):
        with pytest.raises(KeyError):
            acceptance_status(figure_5_2(), "zz")
