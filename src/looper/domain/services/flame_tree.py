"""Turning a list of recorded paths back into the tree they came from.

The simulation records each node with the index of its parent, which
is the cheapest thing it can do on a hot path and leaves one job for
this side: hanging the children back on. That is nearly trivial and
has two parts that are not.

A node whose parent is missing is kept rather than dropped. Pages
arrive one at a time and a recording is a ring, so a reader can
legitimately hold a child whose parent it never saw -- and throwing
those away would quietly shrink the picture. They become roots of
their own, which is what they are as far as anybody can tell.

Children are sorted by what they cost, heaviest first. A flame graph
read left to right then reads worst first, and the order stays put
between two readings of a growing window, which a name order would
not.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from looper.domain.model.profile.flame import Frame

#: The node every path hangs from. It is not a function and is never
#: recorded; a node naming it as a parent is an outermost frame.
ROOT = 0


@dataclass(frozen=True)
class RecordedPath:
    """One node of the tree, as the simulation recorded it.

    Attributes:
        index: Its own position, which its children name as parent.
        parent: The node it was called from, or the root.
        frame: What was measured there, without its children.
    """

    index: int
    parent: int
    frame: Frame


def build_flame(paths: Sequence[RecordedPath]) -> tuple[Frame, ...]:
    """Hang every recorded node under the one that called it.

    Args:
        paths: The nodes, in any order.

    Returns:
        The outermost frames, heaviest first.
    """
    children = _children_of(paths)
    known = {one.index for one in paths}
    roots = [one for one in paths if one.parent == ROOT or one.parent not in known]
    return _heaviest_first(tuple(_assemble(one, children) for one in roots))


def _children_of(paths: Sequence[RecordedPath]) -> Mapping[int, list[RecordedPath]]:
    """Every node, under the index of the node that called it."""
    found: dict[int, list[RecordedPath]] = {}
    for one in paths:
        found.setdefault(one.parent, []).append(one)
    return found


def _assemble(path: RecordedPath, children: Mapping[int, list[RecordedPath]]) -> Frame:
    """One node with everything below it hung on."""
    below = tuple(_assemble(one, children) for one in children.get(path.index, ()))
    return Frame(
        name=path.frame.name,
        origin=path.frame.origin,
        source=path.frame.source,
        calls=path.frame.calls,
        total_nanoseconds=max(path.frame.total_nanoseconds, _spent(below)),
        self_nanoseconds=path.frame.self_nanoseconds,
        children=_heaviest_first(below),
    )


def _heaviest_first(frames: tuple[Frame, ...]) -> tuple[Frame, ...]:
    """The frames in the order a reader wants them: worst first."""
    return tuple(sorted(frames, key=lambda one: (-one.total_nanoseconds, one.name)))


def _spent(frames: tuple[Frame, ...]) -> int:
    """What a set of children cost altogether.

    A parent is never drawn narrower than its children. It cannot
    really be narrower either, but the two numbers are measured at
    different moments -- a call that was still running when the
    window was read has been counted by its children and not yet by
    it -- and a picture is worth more than a complaint.
    """
    return sum(one.total_nanoseconds for one in frames)
