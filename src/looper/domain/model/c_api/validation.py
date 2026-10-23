"""Shared invariants for the parsed C API model."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable


def ensure_non_empty(value: str, subject: str) -> None:
    """Reject a blank identifier.

    Args:
        value: Identifier to check.
        subject: Human readable description used in the error message.

    Raises:
        ValueError: If ``value`` is empty or whitespace only.
    """
    if not value.strip():
        raise ValueError(f"{subject} must not be empty")


def ensure_unique_names(names: Iterable[str], subject: str) -> None:
    """Reject duplicated identifiers within a single scope.

    Args:
        names: Identifiers that share one C scope.
        subject: Human readable description used in the error message.

    Raises:
        ValueError: If any identifier occurs more than once.
    """
    duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
    if duplicates:
        raise ValueError(f"{subject} contains duplicate names: {', '.join(duplicates)}")
