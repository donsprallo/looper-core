"""Laying a call tree out as the bars of a flame graph.

The geometry is three lines of arithmetic and one decision. Each
frame is as wide as its share of the window; its children are laid
side by side within it, in the order the tree already put them; and
the leftover is the part the frame did itself.

The decision is that the leftover is left as a gap rather than drawn
as a bar of its own. Some tools draw self time as a child called
something like "(self)", which reads as a function that does not
exist. A gap under a wide bar says the same thing and cannot be
mistaken for a call.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence

from looper.application.dto.flame_view import FlameView, FrameView
from looper.domain.model.profile import Flame, Frame

#: Bars narrower than this are not drawn. At a thousand pixels a
#: tenth of a percent is one pixel, and a picture made mostly of
#: single pixels is slower to draw and no easier to read.
NARROWEST = 0.001

#: Said when the simulation ran out of room for paths.
LOST_PATHS = "paths were not recorded; the picture is missing branches"

#: Said when nobody has asked for the paths to be followed.
NOT_WATCHED = "nobody is following the calls, so there is nothing to draw"


def build_flame_view(flame: Flame) -> FlameView:
    """Lay a whole window out as bars."""
    total = flame.total_nanoseconds
    return FlameView(
        frames=tuple(_laid_out(flame.roots, total, depth=0, start=0.0)),
        depth=flame.depth,
        total=_duration(total),
        note=_note(flame),
        is_watched=flame.is_watched,
    )


def _laid_out(
    frames: Sequence[Frame], window: int, depth: int, start: float
) -> Iterator[FrameView]:
    """Every frame of one row, and everything stacked on each of them."""
    offset = start
    for frame in frames:
        width = frame.share_of(window)
        if width >= NARROWEST:
            yield _bar(frame, depth, offset, width)
            yield from _laid_out(frame.children, window, depth + 1, offset)
        offset += width


def _bar(frame: Frame, depth: int, start: float, width: float) -> FrameView:
    """One frame as the rectangle it is drawn as."""
    return FrameView(
        name=frame.name,
        origin=frame.origin.value,
        depth=depth,
        start=start,
        width=width,
        calls=frame.calls,
        total=_duration(frame.total_nanoseconds),
        own=_duration(frame.self_nanoseconds),
        share=width,
    )


def _note(flame: Flame) -> str:
    """What is worth saying about the window as a whole."""
    if not flame.is_watched:
        return NOT_WATCHED
    if flame.lost_paths:
        return f"{flame.lost_paths} {LOST_PATHS}"
    return ""


def _duration(nanoseconds: int) -> str:
    """A length of time as a person reads it."""
    if nanoseconds < 1_000:
        return f"{nanoseconds} ns"
    if nanoseconds < 1_000_000:
        return f"{nanoseconds / 1e3:.1f} us"
    if nanoseconds < 1_000_000_000:
        return f"{nanoseconds / 1e6:.1f} ms"
    return f"{nanoseconds / 1e9:.2f} s"
