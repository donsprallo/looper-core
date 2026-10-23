"""Function declared in an adapter header."""

from __future__ import annotations

from dataclasses import dataclass, field

from looper.domain.model.c_api.c_parameter import CParameter
from looper.domain.model.c_api.c_type import CType, CTypeKind
from looper.domain.model.c_api.validation import ensure_non_empty, ensure_unique_names


@dataclass(frozen=True)
class CFunction:
    """A public adapter function that the simulation has to provide.

    Attributes:
        name: Function name as declared in the header.
        return_type: Declared return type.
        parameters: Declared parameters in source order.
        documentation: Raw doc comment attached to the declaration, if any.
    """

    name: str
    return_type: CType
    parameters: tuple[CParameter, ...] = field(default_factory=tuple)
    documentation: str | None = None

    def __post_init__(self) -> None:
        ensure_non_empty(self.name, "A function name")
        ensure_unique_names(
            (parameter.name for parameter in self.parameters),
            f"Function '{self.name}'",
        )

    @property
    def returns_value(self) -> bool:
        """Whether the function has a return value a simulation must produce."""
        return self.return_type.kind is not CTypeKind.VOID

    @property
    def parameter_names(self) -> tuple[str, ...]:
        """Names of all declared parameters in source order."""
        return tuple(parameter.name for parameter in self.parameters)

    def has_parameter(self, name: str) -> bool:
        """Report whether a parameter with the given name is declared."""
        return name in self.parameter_names

    def parameter(self, name: str) -> CParameter:
        """Look up a declared parameter by name.

        Raises:
            KeyError: If the function declares no such parameter.
        """
        for parameter in self.parameters:
            if parameter.name == name:
                return parameter
        raise KeyError(f"Function '{self.name}' has no parameter '{name}'")
