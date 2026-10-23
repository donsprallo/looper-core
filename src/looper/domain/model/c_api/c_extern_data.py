"""Module level data symbols exported by an adapter header."""

from __future__ import annotations

from dataclasses import dataclass

from looper.domain.model.c_api.c_type import CType, CTypeKind
from looper.domain.model.c_api.validation import ensure_non_empty


@dataclass(frozen=True)
class CExternData:
    """An ``extern`` data symbol the simulation has to define.

    Adapter headers export interface tables such as ``mcu_gpio_interface``
    alongside their functions. A generated adapter is incomplete unless it
    defines these symbols too, so they are modelled explicitly instead of
    being treated as a parsing side effect.

    Attributes:
        name: Symbol name as declared in the header.
        type: Declared symbol type.
    """

    name: str
    type: CType

    def __post_init__(self) -> None:
        ensure_non_empty(self.name, "An extern data name")

    @property
    def is_interface_table(self) -> bool:
        """Whether the symbol is a record, which is how vtables are declared."""
        return self.type.kind is CTypeKind.RECORD
