"""Translation of a memory report into something a client can print."""

from __future__ import annotations

from looper.application.dto import (
    AllocationSiteView,
    HeapUsageView,
    MemoryView,
    StackFrameView,
    StackUsageView,
    StaticMemoryView,
    StaticObjectView,
)
from looper.domain.model.memory import (
    AllocationSite,
    HeapUsage,
    StackFrame,
    StackUsage,
    StaticMemoryReport,
    StaticObject,
    kibibytes,
)

#: How many objects a summary names before a reader stops reading.
BIGGEST_SHOWN = 10

#: How many directories it names, for the same reason.
DIRECTORIES_SHOWN = 8

#: How many frames and allocation sites a summary names.
FRAMES_SHOWN = 12


def build_static_memory_view(report: StaticMemoryReport) -> StaticMemoryView:
    """Describe what a build holds statically."""
    return StaticMemoryView(
        biggest=tuple(_object_view(one) for one in report.biggest(BIGGEST_SHOWN)),
        by_directory=tuple(
            (directory or "unknown source", kibibytes(size))
            for directory, size in report.by_directory()[:DIRECTORIES_SHOWN]
        ),
        object_count=len(report.objects),
        total_bytes=report.total_bytes,
        writable_bytes=report.writable_bytes,
        firmware_bytes=report.firmware_bytes,
        budget_bytes=report.budget_bytes,
        is_within_budget=report.is_within_budget,
        total_text=kibibytes(report.total_bytes),
        writable_text=kibibytes(report.writable_bytes),
        firmware_text=kibibytes(report.firmware_bytes),
    )


def _object_view(one: StaticObject) -> StaticObjectView:
    """Describe one object."""
    return StaticObjectView(
        name=one.name,
        origin=one.origin.value,
        directory=one.directory,
        file_name=one.file_name,
        bytes_used=one.bytes_used,
        size_text=kibibytes(one.bytes_used),
        is_constant=one.is_constant,
    )


def build_memory_view(static: StaticMemoryReport, stack: StackUsage, heap: HeapUsage) -> MemoryView:
    """Describe where a simulation's memory goes, in all three places."""
    return MemoryView(
        static=build_static_memory_view(static),
        stack=_stack_view(stack),
        heap=_heap_view(heap),
    )


def _stack_view(stack: StackUsage) -> StackUsageView:
    """Describe how deep the firmware went."""
    return StackUsageView(
        path=tuple(_frame_view(one) for one in stack.path),
        largest=tuple(_frame_view(one) for one in stack.largest_frames(FRAMES_SHOWN)),
        deepest_bytes=stack.deepest_bytes,
        deepest_depth=stack.deepest_depth,
        deepest_text=kibibytes(stack.deepest_bytes),
        path_is_complete=stack.path_is_complete,
        is_measured=not stack.is_empty,
    )


def _frame_view(frame: StackFrame) -> StackFrameView:
    """Describe one function on the stack."""
    return StackFrameView(
        function=frame.function,
        origin=frame.origin.value,
        file_name=frame.file_name,
        bytes_used=frame.bytes_used,
        size_text=kibibytes(frame.bytes_used),
    )


def _heap_view(heap: HeapUsage) -> HeapUsageView:
    """Describe what the allocator was asked for."""
    return HeapUsageView(
        outstanding=tuple(_site_view(one) for one in heap.heaviest(FRAMES_SHOWN)),
        allocations=heap.allocations,
        frees=heap.frees,
        failures=heap.failures,
        live_text=kibibytes(heap.live_bytes),
        peak_text=kibibytes(heap.peak_bytes),
        firmware_text=kibibytes(heap.firmware_outstanding_bytes),
        untracked_blocks=heap.untracked_blocks,
        never_allocated=heap.never_allocated,
        is_watched=heap.is_watched,
    )


def _site_view(site: AllocationSite) -> AllocationSiteView:
    """Describe one place that is holding something."""
    return AllocationSiteView(
        function=site.function,
        origin=site.origin.value,
        file_name=site.file_name,
        blocks=site.blocks,
        bytes_used=site.bytes_used,
        size_text=kibibytes(site.bytes_used),
    )
