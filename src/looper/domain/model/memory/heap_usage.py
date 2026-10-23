"""What the firmware asked the allocator for, and what it gave back.

Much embedded firmware is not allowed to allocate at all after start
up, and the rule is usually kept by reading the code. A simulation can
answer it instead: every call to the allocator passes through a wrapper
the linker puts in front of it, so "this firmware never allocates" and
"this firmware leaks a buffer per frame" are both measurements.

The sizes transfer. A ``malloc(256)`` asks for 256 bytes on a host and
on a target; what differs is the allocator's own overhead and how badly
it fragments, neither of which this claims to know.

The one thing to watch when reading a heap report is whose allocations
they are. A C runtime allocates for its own reasons -- a buffer for the
first thing that is printed, something for the locale -- and those are
in here too, because the wrapper cannot tell who is calling until the
call site is given a name. So every allocation carries its origin, and
the firmware's own are the ones to look at.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePath

from looper.domain.model.sources import FunctionOrigin


@dataclass(frozen=True)
class AllocationSite:
    """One place that allocated, and what is still out from it.

    Attributes:
        function: Function the allocation was made from.
        origin: Which part of the simulation that function belongs to.
        source: File it was compiled from, when one is known.
        blocks: Blocks from here that have not been freed.
        bytes_used: What those blocks add up to.
    """

    function: str
    origin: FunctionOrigin
    source: PurePath | None = None
    blocks: int = 0
    bytes_used: int = 0

    def __post_init__(self) -> None:
        if not self.function:
            raise ValueError("An allocation site has a name")
        if (self.blocks < 0) or (self.bytes_used < 0):
            raise ValueError(f"'{self.function}' cannot hold a negative amount")

    @property
    def file_name(self) -> str:
        """The source file alone, without the path to it."""
        return self.source.name if self.source is not None else ""


@dataclass(frozen=True)
class HeapUsage:
    """What passed through the allocator over one window.

    Attributes:
        allocations: Calls that returned a block.
        frees: Blocks given back.
        failures: Calls the allocator could not satisfy.
        live_bytes: What is out now.
        peak_bytes: The most that was ever out at once.
        outstanding: Where what is still out came from.
        untracked_blocks: Blocks freed that the table had never seen,
            which is what a block allocated before the window began
            looks like. Counted rather than subtracted, so that the
            live figure cannot drift below nothing.
        is_watched: Whether this build has the allocator wrapped at all.
    """

    allocations: int = 0
    frees: int = 0
    failures: int = 0
    live_bytes: int = 0
    peak_bytes: int = 0
    outstanding: tuple[AllocationSite, ...] = field(default_factory=tuple)
    untracked_blocks: int = 0
    is_watched: bool = False

    def __post_init__(self) -> None:
        for name in ("allocations", "frees", "failures", "live_bytes", "peak_bytes"):
            if getattr(self, name) < 0:
                raise ValueError(f"A heap {name.replace('_', ' ')} count is not negative")

    @property
    def never_allocated(self) -> bool:
        """Whether nothing asked the allocator for anything.

        The answer a project that forbids dynamic memory wants, and it
        is only meaningful in a build that is watching: an unwatched
        one reports nothing because it is not looking.
        """
        return self.is_watched and (self.allocations == 0)

    @property
    def outstanding_blocks(self) -> int:
        """Blocks that have not been given back."""
        return sum(site.blocks for site in self.outstanding)

    @property
    def firmware_outstanding(self) -> tuple[AllocationSite, ...]:
        """What is still out from the firmware's own code.

        What a C runtime holds for itself is not a leak in the firmware
        and is the bulk of what a short window sees, so the two are
        kept apart rather than added up.
        """
        return tuple(site for site in self.outstanding if site.origin.is_the_firmware_itself)

    @property
    def firmware_outstanding_bytes(self) -> int:
        """What the firmware's own outstanding blocks add up to."""
        return sum(site.bytes_used for site in self.firmware_outstanding)

    def heaviest(self, count: int) -> tuple[AllocationSite, ...]:
        """The sites holding the most."""
        ordered = sorted(self.outstanding, key=lambda one: (-one.bytes_used, one.function))
        return tuple(ordered[:count])
