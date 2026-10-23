"""One adapter header translated into a declaration set."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from looper.domain.model.c_api.c_enum import CEnum
from looper.domain.model.c_api.c_extern_data import CExternData
from looper.domain.model.c_api.c_function import CFunction
from looper.domain.model.c_api.c_record import CRecord
from looper.domain.model.c_api.validation import ensure_non_empty, ensure_unique_names


@dataclass(frozen=True)
class AdapterModule:
    """All public declarations of a single adapter header.

    Attributes:
        name: Short module name such as ``gpio``.
        header_path: Path of the header the declarations were read from.
        functions: Public functions in source order.
        records: Struct and union declarations in source order.
        enums: Enumeration declarations in source order.
        extern_data: Exported data symbols in source order.
    """

    name: str
    header_path: Path
    functions: tuple[CFunction, ...] = field(default_factory=tuple)
    records: tuple[CRecord, ...] = field(default_factory=tuple)
    enums: tuple[CEnum, ...] = field(default_factory=tuple)
    extern_data: tuple[CExternData, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        ensure_non_empty(self.name, "A module name")
        ensure_unique_names(self.function_names, f"Module '{self.name}'")
        ensure_unique_names(
            (symbol.name for symbol in self.extern_data),
            f"Module '{self.name}' extern data",
        )

    @property
    def function_names(self) -> tuple[str, ...]:
        """Names of all public functions in source order."""
        return tuple(function.name for function in self.functions)

    def function(self, name: str) -> CFunction:
        """Look up a public function by name.

        Raises:
            KeyError: If the module declares no such function.
        """
        for function in self.functions:
            if function.name == name:
                return function
        raise KeyError(f"Module '{self.name}' has no function '{name}'")
