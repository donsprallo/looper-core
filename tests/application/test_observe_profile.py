"""Giving the addresses in a profile their names back.

The simulation reports where a function sits in a process that has been
relocated; the debug information describes where it was linked. Getting
that subtraction wrong turns every name into a wrong name, which is the
one failure a profile must not have.
"""

from __future__ import annotations

from pathlib import Path, PurePath

from simulation_doubles import RecordingSession

from looper.application.queries import ObserveProfile
from looper.domain.model.firmware import FunctionSymbol, StaticSymbol
from looper.domain.model.profile import MeasuredFunction
from looper.domain.model.sources import SourceLayout
from looper.domain.ports import DebugInformationReader

EXECUTABLE = Path("build") / "demo.exe"
LINK_TIME_BASE = 0x1_4000_0000
RUNTIME_BASE = 0x7FF7_0000_0000
SLIDE = RUNTIME_BASE - LINK_TIME_BASE

APP = PurePath("C:/fw/app/Src/app.c")
MODEL = PurePath("C:/project/src/board.c")
RUNTIME = PurePath("C:/looper/runtime/src/looper_clock.c")

SYMBOLS = (
    FunctionSymbol("app_run", 0x1_4000_1000, APP),
    FunctionSymbol("model_spi", 0x1_4000_2000, MODEL),
    FunctionSymbol("looper_now", 0x1_4000_3000, RUNTIME),
)

LAYOUT = SourceLayout(
    runtime=(PurePath("C:/looper/runtime"),),
    device_model=(PurePath("C:/project/src"),),
    firmware=(PurePath("C:/fw"),),
)


class StubReader(DebugInformationReader):
    """A debug reader answering from a fixed description."""

    def __init__(self, failure: str | None = None) -> None:
        self._failure = failure
        self.reads = 0

    def read_link_time_base(self, executable: Path) -> int:
        return LINK_TIME_BASE

    def read_variables(self, executable: Path) -> tuple[()]:
        return ()

    def read_statics(self, executable: Path) -> tuple[StaticSymbol, ...]:
        return ()

    def read_functions(self, executable: Path) -> tuple[FunctionSymbol, ...]:
        if self._failure is not None:
            raise ValueError(self._failure)
        self.reads += 1
        return SYMBOLS


def measured(address: int, self_nanoseconds: int, calls: int = 1) -> MeasuredFunction:
    """One measurement as the simulation reports it, already relocated."""
    return MeasuredFunction(
        address=address + SLIDE,
        calls=calls,
        total_nanoseconds=self_nanoseconds,
        self_nanoseconds=self_nanoseconds,
    )


def a_session(*measurements: MeasuredFunction) -> RecordingSession:
    """A session reporting the given profile."""
    session = RecordingSession(executable=EXECUTABLE, runtime_base=RUNTIME_BASE)
    session.measurements = measurements
    return session


def test_an_address_is_given_the_name_of_what_sits_there() -> None:
    session = a_session(measured(0x1_4000_1000, 500))

    view = ObserveProfile(session, StubReader(), LAYOUT).execute()

    entry = view.groups[0].children[0].children[0].entry
    assert entry is not None
    assert entry.name == "app_run"
    assert entry.file_name == "app.c"


def test_the_origin_comes_from_the_file_it_was_compiled_from() -> None:
    session = a_session(
        measured(0x1_4000_1000, 600),
        measured(0x1_4000_2000, 300),
        measured(0x1_4000_3000, 100),
    )

    view = ObserveProfile(session, StubReader(), LAYOUT).execute()

    assert [group.label for group in view.groups] == ["firmware", "device model", "runtime"]
    assert view.groups[0].share_text == "60.0%"


def test_an_address_nothing_describes_keeps_its_number() -> None:
    """Better a hexadecimal name than a wrong one."""
    session = a_session(measured(0x1_4009_9000, 100))

    view = ObserveProfile(session, StubReader(), LAYOUT).execute()

    entry = view.groups[0].children[0].children[0].entry
    assert entry is not None
    assert entry.name.startswith("0x")
    assert entry.origin == "library"


def test_the_debug_information_is_read_once_and_kept() -> None:
    """Parsing it on every reading would lengthen the window it measures."""
    session = a_session(measured(0x1_4000_1000, 100))
    reader = StubReader()
    profile = ObserveProfile(session, reader, LAYOUT)

    profile.execute()
    profile.execute()

    assert reader.reads == 1


def test_a_build_nothing_instrumented_says_so_rather_than_showing_nothing() -> None:
    view = ObserveProfile(a_session(), StubReader(), LAYOUT).execute()

    assert not view.is_profiling
    assert "profile = true" in view.note


def test_a_window_that_measured_something_says_what_it_accounted_for() -> None:
    session = a_session(measured(0x1_4000_1000, 2_500_000))

    view = ObserveProfile(session, StubReader(), LAYOUT).execute()

    assert view.note == "1 functions, 2.50 ms accounted for"


def test_clearing_reaches_the_simulation() -> None:
    session = a_session()

    ObserveProfile(session, StubReader(), LAYOUT).clear()

    assert session.cleared == ["profile"]
