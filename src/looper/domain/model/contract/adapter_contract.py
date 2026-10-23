"""Explicit semantics for a complete adapter surface."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from looper.domain.model.c_api.validation import ensure_unique_names
from looper.domain.model.contract.bus_role import BusRole
from looper.domain.model.contract.function_contract import FunctionContract


@dataclass(frozen=True)
class AdapterContract:
    """All hand written semantics that complement the parsed declarations.

    Attributes:
        functions: Contracts for the functions that carry extra semantics.
        roles: What a function does, for the functions that use a bus. A
            contract without them describes a stub; with them the generator
            can write the behaviour too.
    """

    functions: tuple[FunctionContract, ...] = field(default_factory=tuple)
    roles: Mapping[str, BusRole] = field(default_factory=dict)

    def __post_init__(self) -> None:
        ensure_unique_names(self.contracted_function_names, "The adapter contract")

    @property
    def contracted_function_names(self) -> tuple[str, ...]:
        """Names of all functions covered by this contract."""
        return tuple(contract.function_name for contract in self.functions)

    def covers(self, function_name: str) -> bool:
        """Report whether the given function has an explicit contract."""
        return function_name in self.contracted_function_names

    def role(self, function_name: str) -> BusRole | None:
        """What a function does on a bus, or ``None`` when it says nothing."""
        return self.roles.get(function_name)

    def function(self, function_name: str) -> FunctionContract:
        """Look up the contract of a single function.

        Raises:
            KeyError: If the function has no explicit contract.
        """
        for contract in self.functions:
            if contract.function_name == function_name:
                return contract
        raise KeyError(f"The adapter contract does not cover '{function_name}'")
