import pytest

from argumentation import ArgumentationFramework
from argumentation.examples import figure_5_1, figure_5_2


@pytest.fixture
def fig51():
    return figure_5_1()


class TestConstruction:
    def test_attackers_and_targets(self, fig51):
        assert fig51.attackers("a1") == {"a2", "a4"}
        assert fig51.attacked_by("a3") == {"a2"}
        assert fig51.attackers("a3") == set()

    def test_rejects_attack_on_unknown_argument(self):
        with pytest.raises(ValueError):
            ArgumentationFramework(["a"], [("a", "b")])

    def test_rejects_unknown_argument_in_query(self, fig51):
        with pytest.raises(KeyError):
            fig51.is_conflict_free({"a1", "zz"})

    def test_plus(self, fig51):
        assert fig51.plus({"a3", "a5"}) == {"a2", "a4"}
        assert fig51.plus(set()) == set()

    def test_equality(self):
        assert figure_5_2() == figure_5_2()
        assert figure_5_1() != figure_5_2()


class TestConflictFree:
    def test_empty_set(self, fig51):
        assert fig51.is_conflict_free(set())

    def test_conflict_free_set(self, fig51):
        assert fig51.is_conflict_free({"a1", "a3", "a5"})

    def test_set_with_internal_attack(self, fig51):
        assert not fig51.is_conflict_free({"a2", "a3"})

    def test_self_attacking_argument(self):
        af = ArgumentationFramework(["a"], [("a", "a")])
        assert not af.is_conflict_free({"a"})


class TestDefence:
    def test_book_example(self, fig51):
        # "In Figure 5.1, for example, {α3, α5} defends α1."
        assert fig51.defends({"a3", "a5"}, "a1")

    def test_partial_defence_is_not_enough(self, fig51):
        assert not fig51.defends({"a3"}, "a1")

    def test_unattacked_argument_defended_by_empty_set(self, fig51):
        assert fig51.defends(set(), "a3")


class TestCharacteristicFunction:
    def test_example_5_6(self, fig51):
        assert fig51.characteristic({"a3"}) == {"a3", "a5"}
        assert fig51.characteristic({"a5"}) == {"a3", "a5"}
        assert fig51.characteristic({"a1", "a3", "a5"}) == {"a1", "a3", "a5"}

    def test_grounded_iteration_steps(self, fig51):
        # F¹(∅) = {α3, α5}; F²(∅) = {α1, α3, α5}; F³(∅) = F²(∅)
        f1 = fig51.characteristic(set())
        f2 = fig51.characteristic(f1)
        assert f1 == {"a3", "a5"}
        assert f2 == {"a1", "a3", "a5"}
        assert fig51.characteristic(f2) == f2


class TestAdmissibleAndComplete:
    @pytest.mark.parametrize(
        "s", [set(), {"a3"}, {"a5"}, {"a3", "a5"}, {"a1", "a3", "a5"}]
    )
    def test_example_5_5_admissible_sets(self, fig51, s):
        assert fig51.is_admissible(s)

    def test_undefended_set_is_not_admissible(self, fig51):
        assert not fig51.is_admissible({"a1"})

    def test_example_5_6_complete(self, fig51):
        assert fig51.is_complete({"a1", "a3", "a5"})
        for s in [set(), {"a3"}, {"a5"}, {"a3", "a5"}]:
            assert not fig51.is_complete(s)

    @pytest.mark.parametrize("s", [{"a3"}, {"a1", "a3"}, {"a2", "a3"}])
    def test_example_5_7_complete_extensions(self, s):
        assert figure_5_2().is_complete(s)

    def test_example_5_7_non_complete(self):
        af = figure_5_2()
        assert af.is_admissible({"a1"})
        assert not af.is_complete({"a1"})
        assert not af.is_complete({"a1", "a2", "a3"})
