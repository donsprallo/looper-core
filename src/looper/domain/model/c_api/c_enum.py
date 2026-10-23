"""Enumeration declarations used by an adapter API."""

from __future__ import annotations

from dataclasses import dataclass, field

from looper.domain.model.c_api.validation import ensure_non_empty, ensure_unique_names


@dataclass(frozen=True)
class CEnumerator:
    """A single named enumeration constant.

    Attributes:
        name: Constant name as declared in the header.
        value: Resolved integer value of the constant.
    """

    name: str
    value: int

    def __post_init__(self) -> None:
        ensure_non_empty(self.name, "An enumerator name")


@dataclass(frozen=True)
class CEnum:
    """An enumeration that the generated simulation has to mirror.

    Attributes:
        name: Type name used by the adapter API.
        enumerators: Declared constants in source order.
    """

    name: str
    enumerators: tuple[CEnumerator, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        ensure_non_empty(self.name, "An enum name")
        ensure_unique_names(
            (enumerator.name for enumerator in self.enumerators),
            f"Enum '{self.name}'",
        )

    @property
    def enumerator_names(self) -> tuple[str, ...]:
        """Names of all declared constants in source order."""
        return tuple(enumerator.name for enumerator in self.enumerators)
