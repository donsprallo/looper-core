"""Where a simulation's memory goes: statically, on the stack, on the heap.

Three questions that are usually asked together and answered by three
different means. What a build holds before it runs is in its debug
information. How deep the stack went is what the instrumentation hooks
see. What the allocator was asked for is what a wrapper in front of it
records.

None of them gives a target's numbers, and the models say so where it
matters. What they give is the firmware's own structure: which object
is large, which call path is deep, which function allocates.
"""

from __future__ import annotations

from looper.domain.model.memory.heap_reading import HeapReading, MeasuredSite
from looper.domain.model.memory.heap_usage import AllocationSite, HeapUsage
from looper.domain.model.memory.stack_usage import StackFrame, StackUsage
from looper.domain.model.memory.static_memory import (
    StaticMemoryReport,
    StaticObject,
    kibibytes,
)

__all__ = [
    "AllocationSite",
    "HeapReading",
    "HeapUsage",
    "MeasuredSite",
    "StackFrame",
    "StackUsage",
    "StaticMemoryReport",
    "StaticObject",
    "kibibytes",
]
