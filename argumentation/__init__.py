"""Abstract argumentation semantics and strategic argumentation."""

from argumentation.acceptance import Status, acceptance_report, acceptance_status
from argumentation.framework import ArgumentationFramework
from argumentation.labelling import Label, legal_labellings
from argumentation.semantics import (
    complete_extensions,
    extensions,
    grounded,
    preferred_extensions,
    semi_stable_extensions,
    stable_extensions,
)

__all__ = [
    "ArgumentationFramework",
    "Label",
    "Status",
    "acceptance_report",
    "acceptance_status",
    "complete_extensions",
    "extensions",
    "grounded",
    "legal_labellings",
    "preferred_extensions",
    "semi_stable_extensions",
    "stable_extensions",
]
__version__ = "0.1.0"
