"""Translation of what the simulation measured of itself.

Apart from the rest because it is a different subject: the profile,
the heap and the timings describe the programme rather than the board
it is pretending to be, and they arrive in whole-response shapes
rather than one message at a time.
"""

from __future__ import annotations

from looper.domain.model.measurement import Distribution
from looper.domain.model.memory import HeapReading, MeasuredSite
from looper.domain.model.profile import (
    MeasuredFunction,
    MeasuredPath,
    PathReading,
    ProfileReading,
)
from looper.domain.model.simulation import CallTiming
from looper.infrastructure.ipc.generated import looper_control_pb2 as protocol


def to_measured_function(profile: protocol.Profile) -> MeasuredFunction:
    """Translate one profiled function into its domain representation."""
    return MeasuredFunction(
        address=profile.address,
        calls=profile.calls,
        total_nanoseconds=profile.total_nanoseconds,
        self_nanoseconds=profile.self_nanoseconds,
        longest_nanoseconds=profile.longest_nanoseconds,
        frame_bytes=profile.frame_bytes,
    )


def to_profile_page(response: protocol.Response) -> ProfileReading:
    """Translate one reply's worth of a profile."""
    return ProfileReading(
        measurements=tuple(to_measured_function(profile) for profile in response.profiles),
        next_position=response.next_sequence,
        lost=response.lost_profiles,
        is_profiling=response.profiling,
        deepest_stack_bytes=response.stack_deepest_bytes,
        deepest_depth=response.stack_deepest_depth,
        stack_path=tuple(response.stack_path),
        stack_path_is_complete=response.stack_path_complete,
    )


def to_heap_reading(response: protocol.Response) -> HeapReading:
    """Translate what the allocator was asked for."""
    heap = response.heap
    return HeapReading(
        allocations=heap.allocations,
        frees=heap.frees,
        failures=heap.failures,
        live_bytes=heap.live_bytes,
        peak_bytes=heap.peak_bytes,
        untracked_blocks=heap.untracked_blocks,
        outstanding=tuple(
            MeasuredSite(address=one.site, blocks=one.blocks, bytes_used=one.bytes)
            for one in heap.outstanding
        ),
        is_watched=heap.is_watched,
    )


def to_call_timing(timing: protocol.Timing) -> CallTiming:
    """Translate one function's measurements into its domain representation."""
    return CallTiming(
        function=timing.function,
        calls=timing.calls,
        answered_calls=timing.answered_calls,
        total_nanoseconds=timing.total_nanoseconds,
        shortest_nanoseconds=timing.shortest_nanoseconds,
        longest_nanoseconds=timing.longest_nanoseconds,
        spread=Distribution(tuple(timing.bands)),
    )


def to_measured_path(path: protocol.ProfilePath, index: int) -> MeasuredPath:
    """Translate one node of the tree into its domain representation.

    The index is the node's place in the whole tree rather than in
    the page, because that is what its children name as their parent.
    """
    return MeasuredPath(
        index=index,
        parent=path.parent,
        address=path.address,
        calls=path.calls,
        total_nanoseconds=path.total_nanoseconds,
        self_nanoseconds=path.self_nanoseconds,
    )


def to_path_reading(response: protocol.Response, first_index: int) -> PathReading:
    """Translate one page of the tree of paths."""
    return PathReading(
        paths=tuple(
            to_measured_path(one, first_index + offset)
            for offset, one in enumerate(response.profile_paths)
        ),
        next_position=response.next_sequence,
        lost=response.lost_profile_paths,
        is_watched=response.watching_profile_paths,
    )
