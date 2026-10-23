"""Behaviour of the firmware variable use cases."""

from __future__ import annotations

from pathlib import Path

import pytest
from simulation_doubles import RecordingSession

from looper.application.commands import RemoveWatch, WatchVariable, WriteVariable
from looper.application.dto import VariableView, WatchView
from looper.application.errors import (
    DebugInformationUnavailableError,
    VariableWriteRejectedError,
)
from looper.application.queries import ListFirmwareVariables, ObserveWatches
from looper.domain.model.firmware import (
    FirmwareVariable,
    FunctionSymbol,
    StaticSymbol,
    VariableEncoding,
    VariablePath,
    VariableWatch,
)
from looper.domain.ports import DebugInformationReader

EXECUTABLE = Path("build") / "demo.exe"
LINK_TIME_BASE = 0x1_4000_0000
RUNTIME_BASE = 0x7FF7_0000_0000
SLIDE = RUNTIME_BASE - LINK_TIME_BASE

GAIN = FirmwareVariable(
    path=VariablePath("g_config.channel[0].gain"),
    link_time_address=0x1_4007_1000,
    encoding=VariableEncoding.FLOATING_POINT,
    byte_width=8,
    declared_in="app.c",
)
REVISION = FirmwareVariable(
    path=VariablePath("g_revision"),
    link_time_address=0x1_4007_2000,
    encoding=VariableEncoding.UNSIGNED_INTEGER,
    byte_width=1,
    is_constant=True,
)


class StubReader(DebugInformationReader):
    """A debug reader answering from a fixed description."""

    def __init__(
        self, variables: tuple[FirmwareVariable, ...] = (GAIN, REVISION), failure: str | None = None
    ) -> None:
        self._variables = variables
        self._failure = failure

    def read_link_time_base(self, executable: Path) -> int:
        if self._failure is not None:
            raise ValueError(self._failure)
        return LINK_TIME_BASE

    def read_variables(self, executable: Path) -> tuple[FirmwareVariable, ...]:
        if self._failure is not None:
            raise ValueError(self._failure)
        return self._variables

    def read_statics(self, executable: Path) -> tuple[StaticSymbol, ...]:
        return ()

    def read_functions(self, executable: Path) -> tuple[FunctionSymbol, ...]:
        if self._failure is not None:
            raise ValueError(self._failure)
        return ()


def a_watch_view(
    encoding: str = "unsigned", byte_width: int = 1, is_writable: bool = True
) -> WatchView:
    """Build a watch view, so that a test names only what it is about."""
    return WatchView(
        channel_id=0x8000_0000,
        path="g_counter",
        name="g_counter",
        encoding=encoding,
        byte_width=byte_width,
        runtime_address=RUNTIME_BASE,
        is_writable=is_writable,
        value=0.0,
    )


def test_listing_translates_every_address_into_the_running_process() -> None:
    session = RecordingSession(executable=EXECUTABLE, runtime_base=RUNTIME_BASE)

    listed = ListFirmwareVariables(session, StubReader()).execute()

    assert [variable.path for variable in listed] == ["g_config.channel[0].gain", "g_revision"]
    assert listed[0].runtime_address == GAIN.link_time_address + SLIDE
    assert listed[0].link_time_address == GAIN.link_time_address


def test_a_listed_variable_carries_what_a_client_shows() -> None:
    session = RecordingSession(executable=EXECUTABLE, runtime_base=RUNTIME_BASE)

    gain, revision = ListFirmwareVariables(session, StubReader()).execute()

    assert gain.name == "gain"
    assert gain.root == "g_config"
    assert gain.display_type == "float 8 B"
    assert gain.display_address == "0x140071000"
    assert gain.is_writable
    assert not revision.is_writable


def test_a_simulation_that_cannot_name_its_executable_is_reported() -> None:
    session = RecordingSession(executable=None, runtime_base=RUNTIME_BASE)

    with pytest.raises(DebugInformationUnavailableError, match="did not report"):
        ListFirmwareVariables(session, StubReader()).execute()


def test_an_unreadable_executable_is_reported() -> None:
    session = RecordingSession(executable=EXECUTABLE, runtime_base=RUNTIME_BASE)
    reader = StubReader(failure="carries no debug information")

    with pytest.raises(DebugInformationUnavailableError, match="no debug information"):
        ListFirmwareVariables(session, reader).execute()


def test_watching_sends_the_variable_and_its_translated_address() -> None:
    session = RecordingSession(executable=EXECUTABLE, runtime_base=RUNTIME_BASE)
    listed = ListFirmwareVariables(session, StubReader()).execute()

    watch = WatchVariable(session).execute(listed[0])

    requested, address = session.watched[0]
    assert requested == GAIN
    assert address == GAIN.link_time_address + SLIDE
    assert watch.path == GAIN.path.text
    assert watch.channel_id >= 0x8000_0000


def test_a_listed_variable_survives_the_trip_out_and_back() -> None:
    session = RecordingSession(executable=EXECUTABLE, runtime_base=RUNTIME_BASE)
    listed = ListFirmwareVariables(session, StubReader()).execute()

    WatchVariable(session).execute(listed[1])

    requested, _ = session.watched[0]
    assert requested == REVISION
    assert requested.is_constant


def test_observing_reports_what_each_watch_last_read() -> None:
    session = RecordingSession(executable=EXECUTABLE, runtime_base=RUNTIME_BASE)
    session.watches = (
        VariableWatch(channel=0x8000_0000, variable=GAIN, runtime_address=RUNTIME_BASE, value=2.5),
    )

    observed = ObserveWatches(session).execute()

    assert observed[0].value == 2.5
    assert observed[0].display_value == "2.5"
    assert observed[0].channel_id == 0x8000_0000


def test_removing_a_watch_reaches_the_simulation() -> None:
    session = RecordingSession(executable=EXECUTABLE, runtime_base=RUNTIME_BASE)

    RemoveWatch(session).execute(0x8000_0003)

    assert session.removed == [0x8000_0003]


def test_a_write_within_range_is_sent() -> None:
    session = RecordingSession(executable=EXECUTABLE, runtime_base=RUNTIME_BASE)

    WriteVariable(session).execute(a_watch_view(), 255.0)

    assert session.written == [(0x8000_0000, 255.0)]


def test_a_write_to_a_constant_is_refused_before_it_is_sent() -> None:
    session = RecordingSession(executable=EXECUTABLE, runtime_base=RUNTIME_BASE)

    with pytest.raises(VariableWriteRejectedError, match="declared const"):
        WriteVariable(session).execute(a_watch_view(is_writable=False), 1.0)

    assert session.written == []


def test_a_write_outside_the_range_names_the_range() -> None:
    session = RecordingSession(executable=EXECUTABLE, runtime_base=RUNTIME_BASE)

    with pytest.raises(VariableWriteRejectedError, match="256 is outside the range 0 to 255"):
        WriteVariable(session).execute(a_watch_view(), 256.0)

    assert session.written == []


def test_an_integer_watch_is_shown_without_a_fraction() -> None:
    assert a_watch_view().model_copy(update={"value": 7.0}).display_value == "7"
    view = a_watch_view(encoding="float", byte_width=8)
    assert view.model_copy(update={"value": 0.125}).display_value == "0.125"


def test_a_listed_variable_can_be_rebuilt_into_the_domain_object() -> None:
    session = RecordingSession(executable=EXECUTABLE, runtime_base=RUNTIME_BASE)
    listed: tuple[VariableView, ...] = ListFirmwareVariables(session, StubReader()).execute()

    WatchVariable(session).execute(listed[0])

    requested, _ = session.watched[0]
    assert requested.encoding is VariableEncoding.FLOATING_POINT
    assert requested.byte_width == 8
