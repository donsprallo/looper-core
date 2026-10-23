"""Parameter of a function declared in an adapter header."""

from __future__ import annotations

from dataclasses import dataclass

from looper.domain.model.c_api.c_type import CType
from looper.domain.model.c_api.validation import ensure_non_empty


@dataclass(frozen=True)
class CParameter:
    """A single named function parameter.

    The model requires a name. Anonymous parameters are legal C but carry no
    information for code generation, so the parsing layer has to supply a
    placeholder name before constructing this value object.

    Attributes:
        name: Parameter name as declared in the header.
        type: Declared parameter type.
    """

    name: str
    type: CType

    def __post_init__(self) -> None:
        ensure_non_empty(self.name, "A parameter name")

    @property
    def is_buffer(self) -> bool:
        """Whether the parameter addresses caller owned payload memory."""
        return self.type.carries_memory and not self.type.is_opaque_handle

    @property
    def is_context(self) -> bool:
        """Whether the parameter is an opaque instance or user context handle."""
        return self.type.is_opaque_handle

    @property
    def is_callback(self) -> bool:
        """Whether the parameter is a function pointer invoked by the adapter."""
        return self.type.is_callback
