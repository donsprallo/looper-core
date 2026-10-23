"""Turning what the debug information lists into what a budget is about.

Two things have to be joined. The debug information says how big every
object is and which file it came from; the project's layout says which
part of the simulation that file belongs to. Only then can a report
separate the firmware's own bytes from the runtime's, which is the
difference between a number worth comparing against a target and one
that is mostly looper.
"""

from __future__ import annotations

from collections.abc import Iterable

from looper.domain.model.firmware import StaticSymbol
from looper.domain.model.memory import StaticMemoryReport, StaticObject
from looper.domain.model.sources import SourceLayout


def describe_static_memory(
    symbols: Iterable[StaticSymbol], layout: SourceLayout, budget_bytes: int = 0
) -> StaticMemoryReport:
    """Describe everything a build holds statically.

    Args:
        symbols: Objects read out of the debug information.
        layout: Where each part of the simulation keeps its sources.
        budget_bytes: What the project allows itself, or zero for none.
    """
    return StaticMemoryReport(
        objects=tuple(_object_of(symbol, layout) for symbol in symbols),
        budget_bytes=budget_bytes,
    )


def _object_of(symbol: StaticSymbol, layout: SourceLayout) -> StaticObject:
    """One object, with the part of the simulation it belongs to."""
    return StaticObject(
        name=symbol.name,
        origin=layout.origin_of(symbol.source),
        source=symbol.source,
        bytes_used=symbol.bytes_used,
        is_constant=symbol.is_constant,
    )
