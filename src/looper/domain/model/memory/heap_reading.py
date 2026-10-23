"""What a running simulation reports about its allocator.

Addresses again, for the same reason as the profile: the simulation
has no symbol table and the client already reads the one in the
executable. So a place that allocated is a number here, and becomes a
function and a file on the other side.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MeasuredSite:
    """One place that is holding something, as the simulation reports it.

    Attributes:
        address: Where in the running process the allocation was made.
        blocks: Blocks from here that have not been freed.
        bytes_used: What those blocks add up to.
    """

    address: int
    blocks: int = 0
    bytes_used: int = 0

    def __post_init__(self) -> None:
        if self.address <= 0:
            raise ValueError("An allocation was made somewhere")


@dataclass(frozen=True)
class HeapReading:
    """One reading of what has passed through the allocator.

    Attributes:
        allocations: Calls that returned a block.
        frees: Blocks given back.
        failures: Calls the allocator could not satisfy.
        live_bytes: What is out now.
        peak_bytes: The most that was ever out at once.
        untracked_blocks: Blocks freed that were never seen allocated.
        outstanding: Where what is still out came from.
        is_watched: Whether this build has the allocator wrapped.
    """

    allocations: int = 0
    frees: int = 0
    failures: int = 0
    live_bytes: int = 0
    peak_bytes: int = 0
    untracked_blocks: int = 0
    outstanding: tuple[MeasuredSite, ...] = field(default_factory=tuple)
    is_watched: bool = False
