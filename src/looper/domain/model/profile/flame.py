"""The call tree a flame graph is drawn from.

A ranking answers "which function is expensive". It cannot answer the
question that follows, which is nearly always the real one: expensive
*when called from where*. A function reached from three places has
one row in a ranking and three places in a tree, and two of them are
usually cheap.

The shape is a tree of frames. A frame is one function reached one
way; its total is the time spent in it on that path, and its
children are what it called from there. A drawing lays each frame
out as a bar as wide as its total and the frames it called side by
side within it; which end of the picture the stack grows towards is
the drawing's business and not decided here.

Two rules decide whether such a picture is honest, and both live
here. A child is never wider than its parent, because a caller's
total contains its callees' -- a tree that broke that rule would be
drawing time that was never spent. And the gap between a frame and
its children is its *self* time, which is the only part of the
picture that is really the function's own work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePath

from looper.domain.model.sources import FunctionOrigin

NANOSECONDS_PER_SECOND = 1e9


@dataclass(frozen=True)
class Frame:
    """One function, reached one way, and what it called from there.

    Attributes:
        name: Name the debug information gives it.
        origin: Which part of the simulation it belongs to.
        source: File it was compiled from, when one is known.
        calls: How often it was entered by this path.
        total_nanoseconds: Host time spent in it on this path, with
            everything it called from here included.
        self_nanoseconds: The same with those calls taken away.
        children: What it called from here, heaviest first.
    """

    name: str
    origin: FunctionOrigin
    source: PurePath | None = None
    calls: int = 0
    total_nanoseconds: int = 0
    self_nanoseconds: int = 0
    children: tuple[Frame, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("A frame belongs to a named function")
        if self.self_nanoseconds > self.total_nanoseconds:
            raise ValueError(
                f"'{self.name}' cannot have spent {self.self_nanoseconds} ns of its own "
                f"out of a total of {self.total_nanoseconds} ns"
            )
        if self.children_nanoseconds > self.total_nanoseconds:
            raise ValueError(f"'{self.name}' called for longer than it ran")

    @property
    def children_nanoseconds(self) -> int:
        """Host time this frame spent inside the calls it made."""
        return sum(one.total_nanoseconds for one in self.children)

    @property
    def total_seconds(self) -> float:
        """Host time spent here, as a person reads it."""
        return self.total_nanoseconds / NANOSECONDS_PER_SECOND

    @property
    def is_leaf(self) -> bool:
        """Whether nothing instrumented was called from here."""
        return not self.children

    @property
    def depth(self) -> int:
        """How many frames the deepest path below this one has."""
        return 1 + max((one.depth for one in self.children), default=0)

    @property
    def frame_count(self) -> int:
        """How many frames there are from here down."""
        return 1 + sum(one.frame_count for one in self.children)

    def share_of(self, nanoseconds: int) -> float:
        """What part of a given span this frame accounts for."""
        return self.total_nanoseconds / nanoseconds if nanoseconds > 0 else 0.0


@dataclass(frozen=True)
class Flame:
    """Everything that ran in one window, as the paths it ran by.

    Attributes:
        roots: The outermost frames, heaviest first. More than one is
            ordinary: a firmware entered from a loop and from an
            interrupt has two.
        lost_paths: Paths the simulation had no room to record. A
            picture missing a branch says so rather than looking
            complete.
        is_watched: Whether the paths were being followed at all,
            which tells an empty window from one nobody asked for.
    """

    roots: tuple[Frame, ...] = field(default_factory=tuple)
    lost_paths: int = 0
    is_watched: bool = False

    @property
    def is_empty(self) -> bool:
        """Whether nothing was recorded."""
        return not self.roots

    @property
    def total_nanoseconds(self) -> int:
        """Host time the whole window accounts for."""
        return sum(one.total_nanoseconds for one in self.roots)

    @property
    def depth(self) -> int:
        """How deep the deepest path went."""
        return max((one.depth for one in self.roots), default=0)

    @property
    def frame_count(self) -> int:
        """How many frames the whole picture holds."""
        return sum(one.frame_count for one in self.roots)
