"""The complete API surface a simulation has to implement."""

from __future__ import annotations

from dataclasses import dataclass, field

from looper.domain.model.c_api.adapter_module import AdapterModule
from looper.domain.model.c_api.c_extern_data import CExternData
from looper.domain.model.c_api.c_function import CFunction
from looper.domain.model.c_api.validation import ensure_unique_names


@dataclass(frozen=True)
class AdapterSurface:
    """Every public declaration found in an adapter header directory.

    Function names share one link time namespace across all modules, so the
    surface rejects collisions that individual modules cannot detect.

    Attributes:
        modules: Parsed modules in header name order.
    """

    modules: tuple[AdapterModule, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        ensure_unique_names((module.name for module in self.modules), "The adapter surface")
        ensure_unique_names(
            (function.name for function in self.functions),
            "The adapter surface",
        )

    @property
    def functions(self) -> tuple[CFunction, ...]:
        """Every public function of every module."""
        return tuple(function for module in self.modules for function in module.functions)

    @property
    def extern_data(self) -> tuple[CExternData, ...]:
        """Every exported data symbol of every module."""
        return tuple(symbol for module in self.modules for symbol in module.extern_data)

    @property
    def module_names(self) -> tuple[str, ...]:
        """Names of all parsed modules."""
        return tuple(module.name for module in self.modules)

    def module(self, name: str) -> AdapterModule:
        """Look up a parsed module by name.

        Raises:
            KeyError: If no module with that name was parsed.
        """
        for module in self.modules:
            if module.name == name:
                return module
        raise KeyError(f"The adapter surface has no module '{name}'")
