"""How deep the firmware went, and what it took with it.

A stack overflow on a microcontroller is not a crash with a message; it
is the next variable quietly becoming something else. The two things
worth knowing before that happens are how deep the calls nest and which
functions put large things on the stack, and a host simulation can see
both exactly -- it is the same firmware making the same calls.

What it cannot do is tell you the target's number. The frames are a
different size on a different machine: another calling convention,
another register allocation, and in a woven build nothing is inlined
that otherwise would be. So the depth and the path are the firmware's
own and carry over; the bytes are this build's.

With one exception that matters more than all the rest. A function that
declares ``uint8_t buffer[2048]`` puts 2048 bytes on the stack here and
2048 bytes on the stack there. Large local buffers are what overflow
small stacks, and those this finds exactly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePath

from looper.domain.model.sources import FunctionOrigin


@dataclass(frozen=True)
class StackFrame:
    """One function on the stack, and what it put there.

    Attributes:
        function: Name the debug information gives it.
        origin: Which part of the simulation it belongs to.
        source: File it was compiled from, when one is known.
        bytes_used: Largest frame of this function that was seen.
    """

    function: str
    origin: FunctionOrigin
    source: PurePath | None = None
    bytes_used: int = 0

    def __post_init__(self) -> None:
        if not self.function:
            raise ValueError("A stack frame belongs to a named function")
        if self.bytes_used < 0:
            raise ValueError(f"'{self.function}' cannot use {self.bytes_used} bytes")

    @property
    def file_name(self) -> str:
        """The source file alone, without the path to it."""
        return self.source.name if self.source is not None else ""


@dataclass(frozen=True)
class StackUsage:
    """The deepest the firmware went, and how it got there.

    Attributes:
        deepest_bytes: Host stack in use at the deepest moment.
        deepest_depth: Frames on the stack at that moment.
        path: Those frames, outermost first. Empty when nothing was
            measured, and cut short when the stack went deeper than the
            profiler follows.
        frames: Every function that was on the stack, with the largest
            frame of it that was seen.
        path_is_complete: Whether the path holds every frame or only as
            many as there was room for.
    """

    deepest_bytes: int = 0
    deepest_depth: int = 0
    path: tuple[StackFrame, ...] = field(default_factory=tuple)
    frames: tuple[StackFrame, ...] = field(default_factory=tuple)
    path_is_complete: bool = True

    def __post_init__(self) -> None:
        if self.deepest_bytes < 0 or self.deepest_depth < 0:
            raise ValueError("A stack does not go negative")

    @property
    def is_empty(self) -> bool:
        """Whether anything was measured at all."""
        return self.deepest_depth == 0

    @property
    def path_bytes(self) -> int:
        """What the frames on the deepest path add up to.

        Less than the deepest bytes when the path was cut short, and
        less again because a frame holds more than its locals: a return
        address, saved registers, and whatever the platform aligns to.
        """
        return sum(frame.bytes_used for frame in self.path)

    def largest_frames(self, count: int) -> tuple[StackFrame, ...]:
        """The functions that put the most on the stack."""
        ordered = sorted(self.frames, key=lambda one: (-one.bytes_used, one.function))
        return tuple(ordered[:count])
