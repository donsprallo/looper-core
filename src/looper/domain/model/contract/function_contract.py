"""Explicit semantics for a single adapter function."""

from __future__ import annotations

from dataclasses import dataclass, field

from looper.domain.model.c_api.validation import ensure_non_empty, ensure_unique_names
from looper.domain.model.contract.parameter_contract import ParameterContract


@dataclass(frozen=True)
class FunctionContract:
    """Parameter semantics for one adapter function.

    Attributes:
        function_name: Name of the function this contract applies to.
        parameters: Contracts for the parameters that carry extra semantics.
    """

    function_name: str
    parameters: tuple[ParameterContract, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        ensure_non_empty(self.function_name, "A contract function name")
        ensure_unique_names(
            self.contracted_parameter_names,
            f"Contract for '{self.function_name}'",
        )

    @property
    def contracted_parameter_names(self) -> tuple[str, ...]:
        """Names of all parameters covered by this contract."""
        return tuple(parameter.parameter_name for parameter in self.parameters)

    def covers(self, parameter_name: str) -> bool:
        """Report whether the given parameter has an explicit contract."""
        return parameter_name in self.contracted_parameter_names

    def parameter(self, parameter_name: str) -> ParameterContract:
        """Look up the contract of a single parameter.

        Raises:
            KeyError: If the parameter has no explicit contract.
        """
        for parameter in self.parameters:
            if parameter.parameter_name == parameter_name:
                return parameter
        raise KeyError(f"Contract for '{self.function_name}' does not cover '{parameter_name}'")
