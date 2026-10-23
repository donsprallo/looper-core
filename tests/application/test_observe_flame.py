"""Turning the recorded call tree into the bars of a flame graph.

Three things have to hold. The names come from the same subtraction
the ranking uses, so a relocated address still finds its symbol. The
geometry is honest: a child begins where its parent begins and is
never wider than it. And a window nobody was following is told from
one in which nothing happened, because the two look identical and
mean quite different things.
"""

from __future__ import annotations

from pathlib import Path, PurePath

from simulation_doubles import RecordingSession

from looper.application.queries import ObserveFlame
from looper.domain.model.firmware import FunctionSymbol, StaticSymbol
from looper.domain.model.profile import MeasuredPath
from looper.domain.model.sources import SourceLayout
from looper.domain.ports import DebugInformationReader

EXECUTABLE = Path("build") / "demo.exe"
LINK_TIME_BASE = 0x1_4000_0000
RUNTIME_BASE = 0x7FF7_0000_0000
SLIDE = RUNTIME_BASE - LINK_TIME_BASE

APP = PurePath("C:/fw/app/Src/app.c")
MODEL = PurePath("C:/project/src/board.c")

SYMBOLS = (
    FunctionSymbol("app_run", 0x1_4000_1000, APP),
    FunctionSymbol("model_spi", 0x1_4000_2000, MODEL),
)

LAYOUT = SourceLayout(
    device_model=(PurePath("C:/project/src"),),
    firmware=(PurePath("C:/fw"),),
)

MILLISECOND = 1_000_000


class StubReader(DebugInformationReader):
    """A debug reader answering from a fixed description."""

    def read_link_time_base(self, executable: Path) -> int:
        return LINK_TIME_BASE

    def read_variables(self, executable: Path) -> tuple[()]:
        return ()

    def read_statics(self, executable: Path) -> tuple[StaticSymbol, ...]:
        return ()

    def read_functions(self, executable: Path) -> tuple[FunctionSymbol, ...]:
        return SYMBOLS


def a_path(index: int, parent: int, address: int, total_ms: int, self_ms: int) -> MeasuredPath:
    """One node as the simulation reports it, already relocated."""
    return MeasuredPath(
        index=index,
        parent=parent,
        address=address + SLIDE,
        calls=1,
        total_nanoseconds=total_ms * MILLISECOND,
        self_nanoseconds=self_ms * MILLISECOND,
    )


def a_session(*paths: MeasuredPath, watching: bool = True) -> RecordingSession:
    """A session reporting the given tree."""
    session = RecordingSession(executable=EXECUTABLE, runtime_base=RUNTIME_BASE)
    session.paths = paths
    session.watching_paths = watching
    return session


def test_an_address_is_given_the_name_of_what_sits_there() -> None:
    session = a_session(a_path(1, 0, 0x1_4000_1000, 10, 10))

    view = ObserveFlame(session, StubReader(), LAYOUT).execute()

    assert [bar.name for bar in view.frames] == ["app_run"]
    assert view.frames[0].origin == "firmware"


def test_a_callee_sits_on_its_caller_and_begins_where_it_does() -> None:
    session = a_session(
        a_path(1, 0, 0x1_4000_1000, 10, 6),
        a_path(2, 1, 0x1_4000_2000, 4, 4),
    )

    view = ObserveFlame(session, StubReader(), LAYOUT).execute()

    caller, callee = view.frames
    assert (caller.depth, callee.depth) == (0, 1)
    assert callee.start == caller.start
    assert callee.width < caller.width


def test_the_outermost_bar_fills_the_window() -> None:
    session = a_session(a_path(1, 0, 0x1_4000_1000, 10, 10))

    view = ObserveFlame(session, StubReader(), LAYOUT).execute()

    assert view.frames[0].width == 1.0
    assert view.total == "10.0 ms"


def test_the_same_function_reached_two_ways_is_two_bars() -> None:
    """Which is the whole reason for drawing the tree rather than the list."""
    session = a_session(
        a_path(1, 0, 0x1_4000_1000, 10, 2),
        a_path(2, 1, 0x1_4000_2000, 6, 6),
        a_path(3, 0, 0x1_4000_1000, 4, 2),
        a_path(4, 3, 0x1_4000_2000, 2, 2),
    )

    view = ObserveFlame(session, StubReader(), LAYOUT).execute()

    drawn = [bar.name for bar in view.frames]
    assert drawn.count("model_spi") == 2


def test_nobody_following_is_told_from_nothing_happening() -> None:
    session = a_session(watching=False)

    view = ObserveFlame(session, StubReader(), LAYOUT).execute()

    assert not view.is_watched
    assert "nobody is following" in view.note


def test_a_window_being_followed_in_which_nothing_ran_is_not_an_excuse() -> None:
    view = ObserveFlame(a_session(), StubReader(), LAYOUT).execute()

    assert view.is_watched
    assert view.is_empty
    assert view.note == ""


def test_arming_is_asked_for_once_and_not_repeated() -> None:
    """The simulation begins a new window each time it is armed."""
    session = a_session(watching=False)
    flame = ObserveFlame(session, StubReader(), LAYOUT)

    flame.watch(True)
    flame.watch(True)
    flame.watch(False)

    assert flame.is_watching is False
    assert session.watching_paths is False
