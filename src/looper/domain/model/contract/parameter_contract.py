"""Explicit semantics for a single adapter parameter."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique

from looper.domain.model.c_api.validation import ensure_non_empty


@unique
class ParameterRole(Enum):
    """Direction of data flow through a parameter."""

    INPUT = "input"
    OUTPUT = "output"
    INPUT_OUTPUT = "input_output"
    CALLBACK = "callback"
    CONTEXT = "context"


@unique
class BufferLifetime(Enum):
    """How long an adapter may keep a pointer handed to it.

    ``COPIED`` means the adapter must not retain the pointer past the call.
    ``BORROWED`` means the caller guarantees the memory stays valid until the
    transfer completes, which the generated simulation must honour instead of
    copying.
    """

    NOT_APPLICABLE = "not_applicable"
    COPIED = "copied"
    BORROWED = "borrowed"


@unique
class WriteMoment(Enum):
    """When an output buffer becomes valid for the caller."""

    ON_RETURN = "on_return"
    ON_CALLBACK = "on_callback"


ROLES_ADDRESSING_MEMORY = frozenset(
    {ParameterRole.INPUT, ParameterRole.OUTPUT, ParameterRole.INPUT_OUTPUT}
)
"""Roles for which a buffer lifetime is meaningful."""

ROLES_PRODUCING_OUTPUT = frozenset({ParameterRole.OUTPUT, ParameterRole.INPUT_OUTPUT})
"""Roles for which a write moment is meaningful."""


@dataclass(frozen=True)
class ParameterContract:
    """Semantics of one parameter that the declaration alone cannot express.

    Attributes:
        parameter_name: Name of the parameter this contract applies to.
        role: Direction of data flow.
        lifetime: How long the adapter may retain a supplied pointer.
        written_at: When an output buffer becomes valid for the caller.
    """

    parameter_name: str
    role: ParameterRole
    lifetime: BufferLifetime = BufferLifetime.NOT_APPLICABLE
    written_at: WriteMoment | None = None

    def __post_init__(self) -> None:
        ensure_non_empty(self.parameter_name, "A contract parameter name")
        self._reject_lifetime_without_memory()
        self._reject_write_moment_without_output()

    def _reject_lifetime_without_memory(self) -> None:
        if self.lifetime is BufferLifetime.NOT_APPLICABLE:
            return
        if self.role not in ROLES_ADDRESSING_MEMORY:
            raise ValueError(
                f"Parameter '{self.parameter_name}' declares a buffer lifetime "
                f"but has role {self.role.value}"
            )

    def _reject_write_moment_without_output(self) -> None:
        if self.written_at is None:
            return
        if self.role not in ROLES_PRODUCING_OUTPUT:
            raise ValueError(
                f"Parameter '{self.parameter_name}' declares a write moment "
                f"but has role {self.role.value}"
            )
