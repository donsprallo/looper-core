"""Reading the debug information a built simulation carries."""

from __future__ import annotations

from looper.infrastructure.debug.dwarf_debug_reader import DwarfDebugReader
from looper.infrastructure.debug.errors import DebugInformationError
from looper.infrastructure.debug.scalar_expansion import ExpansionLimits

__all__ = [
    "DebugInformationError",
    "DwarfDebugReader",
    "ExpansionLimits",
]
