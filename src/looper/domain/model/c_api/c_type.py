"""Type representation for symbols declared in HAL adapter headers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique

from looper.domain.model.c_api.validation import ensure_non_empty


@unique
class CTypeKind(Enum):
    """Coarse classification of a C type as far as code generation cares."""

    VOID = "void"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    FLOATING = "floating"
    ENUMERATION = "enumeration"
    RECORD = "record"
    POINTER = "pointer"
    FUNCTION_POINTER = "function_pointer"
    ARRAY = "array"
    UNKNOWN = "unknown"


KINDS_REQUIRING_POINTEE = frozenset({CTypeKind.POINTER, CTypeKind.ARRAY})
"""Kinds that are meaningless without a target type."""


@dataclass(frozen=True)
class CType:
    """A C type exactly as declared in an adapter header.

    Attributes:
        spelling: The type as written in the header, for example ``const uint8_t *``.
        kind: Coarse classification used to select a generation strategy.
        is_const: Whether the type itself carries a ``const`` qualifier.
        pointee: Target type of a pointer or array.
        element_count: Declared element count of a fixed size array.
    """

    spelling: str
    kind: CTypeKind
    is_const: bool = False
    pointee: CType | None = None
    element_count: int | None = None

    def __post_init__(self) -> None:
        ensure_non_empty(self.spelling, "A C type spelling")
        if self.kind in KINDS_REQUIRING_POINTEE and self.pointee is None:
            raise ValueError(f"Type '{self.spelling}' of kind {self.kind.value} requires a pointee")
        if self.element_count is not None and self.element_count < 0:
            raise ValueError(f"Type '{self.spelling}' declares a negative element count")

    @property
    def carries_memory(self) -> bool:
        """Whether the type addresses caller owned memory."""
        return self.kind in KINDS_REQUIRING_POINTEE

    @property
    def is_callback(self) -> bool:
        """Whether the type denotes a function pointer."""
        return self.kind is CTypeKind.FUNCTION_POINTER

    @property
    def is_opaque_handle(self) -> bool:
        """Whether the type is a pointer to an unspecified object."""
        if self.kind is not CTypeKind.POINTER or self.pointee is None:
            return False
        return self.pointee.kind is CTypeKind.VOID

    @property
    def points_to_const(self) -> bool:
        """Whether the addressed memory is read only for the callee."""
        return self.pointee is not None and self.pointee.is_const
