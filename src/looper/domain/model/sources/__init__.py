"""Which part of a simulation a piece of code or of memory came from.

A simulation is four kinds of code in one process: the firmware, the
device model standing in for its board, the generated adapter between
them, and looper's own machinery. Telling them apart is the first thing
any report about a running simulation has to do, whether it is about
time, about stack or about bytes that were never freed.

It is decided by where something was compiled from, which the debug
information says and nobody has to maintain.
"""

from __future__ import annotations

from looper.domain.model.sources.function_origin import FunctionOrigin
from looper.domain.model.sources.source_layout import SourceLayout

__all__ = ["FunctionOrigin", "SourceLayout"]
