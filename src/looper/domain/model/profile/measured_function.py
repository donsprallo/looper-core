"""What a running simulation reports, before anybody knows what it means.

The simulation sends addresses. It has no symbol table and no business
holding one: the executable already carries the debug information that
turns an address into a name and a source file, and the client already
reads that information for the variable browser.

So this is the measurement as it arrives, and `ProfiledFunction` is the
same measurement once it has been given a name.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MeasuredFunction:
    """One function's measurements, identified only by where it sits.

    Attributes:
        address: Where the function sits in the running process.
        calls: How often it was entered.
        total_nanoseconds: Host time between entry and return, callees
            included.
        self_nanoseconds: The same with the callees taken away.
        longest_nanoseconds: The slowest single call.
        frame_bytes: Largest stack frame of it that was seen.
    """

    address: int
    calls: int = 0
    total_nanoseconds: int = 0
    self_nanoseconds: int = 0
    longest_nanoseconds: int = 0
    frame_bytes: int = 0

    def __post_init__(self) -> None:
        if self.address <= 0:
            raise ValueError("A measured function sits at an address")


@dataclass(frozen=True)
class ProfileReading:
    """One reply's worth of a profile.

    A window holds every function that ran, which is more than one frame
    carries, so a reading is a sequence of these.

    Attributes:
        measurements: What this page carried.
        next_position: Where to continue, which stops moving at the end.
        lost: Measurements the simulation had no room for.
        is_profiling: Whether any instrumented function ran at all.
        deepest_stack_bytes: Host stack in use at the deepest moment.
        deepest_depth: Frames on the stack at that moment.
        stack_path: Those frames as addresses, outermost first.
        stack_path_is_complete: Whether the whole path was remembered.
    """

    measurements: tuple[MeasuredFunction, ...] = field(default_factory=tuple)
    next_position: int = 0
    lost: int = 0
    is_profiling: bool = False
    deepest_stack_bytes: int = 0
    deepest_depth: int = 0
    stack_path: tuple[int, ...] = field(default_factory=tuple)
    stack_path_is_complete: bool = True
