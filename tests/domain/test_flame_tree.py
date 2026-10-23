"""The call tree a flame graph is drawn from.

Two rules make such a picture honest, and both are checked here: a
child is never wider than its parent, because a caller's total
contains its callees', and the gap between a frame and its children
is the only part that is really the function's own work.

The third thing worth pinning down is what happens to a node whose
parent never arrived. Pages come one at a time and a recording is a
ring, so a reader legitimately holds orphans -- and dropping them
would quietly shrink the picture.
"""

from __future__ import annotations

import pytest

from looper.domain.model.profile import Flame, Frame
from looper.domain.model.sources import FunctionOrigin
from looper.domain.services import RecordedPath, build_flame

MILLISECOND = 1_000_000


def a_path(
    index: int,
    parent: int,
    name: str,
    total_ms: int = 10,
    self_ms: int = 1,
) -> RecordedPath:
    """One recorded node, as the simulation hands it over."""
    return RecordedPath(
        index=index,
        parent=parent,
        frame=Frame(
            name=name,
            origin=FunctionOrigin.FIRMWARE,
            calls=1,
            total_nanoseconds=total_ms * MILLISECOND,
            self_nanoseconds=self_ms * MILLISECOND,
        ),
    )


def test_a_node_hangs_under_the_one_that_called_it() -> None:
    roots = build_flame(
        [a_path(1, 0, "app_run", 10), a_path(2, 1, "read", 6), a_path(3, 2, "wait", 4)]
    )

    assert [one.name for one in roots] == ["app_run"]
    assert [one.name for one in roots[0].children] == ["read"]
    assert [one.name for one in roots[0].children[0].children] == ["wait"]


def test_the_same_function_reached_two_ways_is_two_frames() -> None:
    """The whole point: expensive when called from where."""
    roots = build_flame(
        [
            a_path(1, 0, "app_run", 10),
            a_path(2, 1, "read", 6),
            a_path(3, 1, "write", 3),
            a_path(4, 2, "wait", 5),
            a_path(5, 3, "wait", 1),
        ]
    )

    under = {one.name: one.children[0].total_nanoseconds for one in roots[0].children}
    assert under == {"read": 5 * MILLISECOND, "write": 1 * MILLISECOND}


def test_the_heaviest_child_comes_first() -> None:
    """Read left to right, a flame graph then reads worst first."""
    roots = build_flame(
        [a_path(1, 0, "app_run", 10), a_path(2, 1, "cheap", 1), a_path(3, 1, "dear", 8)]
    )

    assert [one.name for one in roots[0].children] == ["dear", "cheap"]


def test_a_node_whose_parent_never_arrived_is_kept() -> None:
    """A page may hold a child of something the reader never saw."""
    roots = build_flame([a_path(7, 99, "orphan", 5)])

    assert [one.name for one in roots] == ["orphan"]


def test_a_parent_is_never_narrower_than_its_children() -> None:
    """A call still running is counted by its callees before itself."""
    roots = build_flame([a_path(1, 0, "app_run", total_ms=2), a_path(2, 1, "read", total_ms=9)])

    assert roots[0].total_nanoseconds == 9 * MILLISECOND
    assert roots[0].children_nanoseconds <= roots[0].total_nanoseconds


def test_more_than_one_outermost_frame_is_ordinary() -> None:
    """A firmware entered from a loop and from an interrupt has two."""
    roots = build_flame([a_path(1, 0, "app_run", 10), a_path(2, 0, "isr", 3)])

    assert [one.name for one in roots] == ["app_run", "isr"]


def test_nothing_recorded_is_an_empty_picture() -> None:
    assert build_flame([]) == ()


def test_a_frame_cannot_own_more_than_it_spent() -> None:
    with pytest.raises(ValueError, match="of its own"):
        Frame(
            name="app_run",
            origin=FunctionOrigin.FIRMWARE,
            total_nanoseconds=1,
            self_nanoseconds=2,
        )


def test_a_frame_cannot_call_for_longer_than_it_ran() -> None:
    child = Frame(name="read", origin=FunctionOrigin.FIRMWARE, total_nanoseconds=10)

    with pytest.raises(ValueError, match="called for longer"):
        Frame(
            name="app_run",
            origin=FunctionOrigin.FIRMWARE,
            total_nanoseconds=5,
            children=(child,),
        )


def test_a_picture_knows_how_deep_and_how_wide_it_is() -> None:
    roots = build_flame(
        [a_path(1, 0, "app_run", 10), a_path(2, 1, "read", 6), a_path(3, 2, "wait", 4)]
    )
    flame = Flame(roots=roots, is_watched=True)

    assert flame.depth == 3
    assert flame.frame_count == 3
    assert flame.total_nanoseconds == 10 * MILLISECOND
    assert not flame.is_empty


def test_an_empty_window_is_told_from_one_nobody_asked_for() -> None:
    assert not Flame().is_watched
    assert Flame(is_watched=True).is_empty


def test_a_share_is_of_whatever_it_is_asked_about() -> None:
    frame = Frame(name="read", origin=FunctionOrigin.FIRMWARE, total_nanoseconds=25)

    assert frame.share_of(100) == 0.25
    assert frame.share_of(0) == 0.0
