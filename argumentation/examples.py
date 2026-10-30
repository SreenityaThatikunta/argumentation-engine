"""Argument graphs from Rahwan, "Argumentation among Agents" (Chapter 5).

Arguments are named ``"a1"``, ``"a2"``, ... for the book's α1, α2, ...
"""

from argumentation.framework import ArgumentationFramework


def figure_5_1() -> ArgumentationFramework:
    """α1 has defeaters α2 and α4, which are defeated by α3 and α5."""
    return ArgumentationFramework(
        ["a1", "a2", "a3", "a4", "a5"],
        [("a2", "a1"), ("a4", "a1"), ("a3", "a2"), ("a5", "a4")],
    )


def figure_5_2() -> ArgumentationFramework:
    """α1 and α2 defeat each other; α3 is unattacked."""
    return ArgumentationFramework(
        ["a1", "a2", "a3"],
        [("a1", "a2"), ("a2", "a1")],
    )
