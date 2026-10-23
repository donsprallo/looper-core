"""One function, reached one way, as the simulation recorded it.

The counterpart of `MeasuredFunction` for the tree rather than the
ranking: an address, the node it was called from, and what the calls
by that path cost. Nothing is named here, because the running
process has nothing to name it with -- that is the client's work,
done against the debug information of the build.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MeasuredPath:
    """What was measured of one function reached one way.

    Attributes:
        index: Position of this node in the tree, which its children
            name as their parent.
        parent: The node it was called from. Zero is the root, which
            is not a function and is never sent.
        address: Where the function sits in the running process.
        calls: How often it was entered by this path.
        total_nanoseconds: Host time spent there, callees included.
        self_nanoseconds: The same with the callees taken away.
    """

    index: int
    parent: int = 0
    address: int = 0
    calls: int = 0
    total_nanoseconds: int = 0
    self_nanoseconds: int = 0

    def __post_init__(self) -> None:
        if self.index <= 0:
            raise ValueError("The root is not a measurement and is never sent")
        if self.self_nanoseconds > self.total_nanoseconds:
            raise ValueError("A path cannot own more time than it spent")


@dataclass(frozen=True)
class PathReading:
    """One reply's worth of the tree of paths.

    Attributes:
        paths: What this page carried.
        next_position: Where to continue, which stops moving at the end.
        lost: Paths the simulation had no room to record.
        is_watched: Whether the paths were being followed at all,
            which tells an empty tree from one nobody asked for.
    """

    paths: tuple[MeasuredPath, ...] = field(default_factory=tuple)
    next_position: int = 0
    lost: int = 0
    is_watched: bool = False
