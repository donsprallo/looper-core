"""The three memory reports, against a simulation that was really built.

Everything else about them can be tested with doubles. What cannot is
whether the numbers mean anything: that the compiler's own frame
layout is what the hooks measure, that a return address resolves to
the function it was taken in, and that an object's size is the one the
compiler chose rather than the one a header suggests.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from conftest import DEFINITION

from looper.application.dto import MemoryView
from looper.application.queries import ObserveMemory
from looper.infrastructure.build import TomlBuildDefinitionRepository
from looper.infrastructure.debug import DwarfDebugReader
from looper.infrastructure.ipc import ProtobufSimulationSession
from looper.infrastructure.profile_layout import layout_of

WINDOW_SECONDS = 0.3


@pytest.fixture
def memory(real_time_session: ProtobufSimulationSession) -> Iterator[MemoryView]:
    """One reading of where the example keeps its memory."""
    definition = TomlBuildDefinitionRepository().load(DEFINITION)
    observe = ObserveMemory(
        real_time_session,
        DwarfDebugReader(),
        layout_of(definition),
        definition.memory_budget,
    )
    observe.execute()
    observe.clear()
    time.sleep(WINDOW_SECONDS)
    yield observe.execute()


def test_the_build_holds_something_statically(memory: MemoryView) -> None:
    assert memory.static.object_count > 0
    assert memory.static.writable_bytes > 0
    assert memory.static.firmware_bytes > 0


def test_a_constant_costs_nothing_that_can_be_written(memory: MemoryView) -> None:
    assert memory.static.writable_bytes <= memory.static.total_bytes


def test_every_large_object_is_named_and_placed(memory: MemoryView) -> None:
    for one in memory.static.biggest:
        assert one.name
        assert one.file_name, one.name


def test_the_stack_was_measured_and_the_path_kept(memory: MemoryView) -> None:
    assert memory.stack.is_measured, memory.stack.summary
    assert memory.stack.deepest_depth > 1
    assert len(memory.stack.path) == memory.stack.deepest_depth


def test_every_frame_on_the_path_has_a_name(memory: MemoryView) -> None:
    """An unresolved address keeps its number, so no name means no match."""
    for frame in memory.stack.path:
        assert not frame.function.startswith("0x"), frame.function


def test_the_path_runs_from_the_loop_downward(memory: MemoryView) -> None:
    """The outermost frame is whatever the loop calls, not the loop itself.

    A window begins when a client clears it, which is while the loop is
    already running, so the first frame measured is the first one
    entered after that.
    """
    assert memory.stack.path[0].function == "app_step"


def test_no_frame_claims_more_than_the_whole_stack(memory: MemoryView) -> None:
    for frame in memory.stack.largest:
        assert frame.bytes_used <= memory.stack.deepest_bytes, frame.function


def test_the_example_never_allocates(memory: MemoryView) -> None:
    """Which is a property of the firmware, now measured rather than assumed."""
    assert memory.heap.is_watched, memory.heap.summary
    assert memory.heap.never_allocated, memory.heap.summary


def test_what_the_runtime_library_holds_is_not_the_firmware_s(
    memory: MemoryView,
) -> None:
    """A C runtime allocates for itself, and that is not a leak here."""
    for site in memory.heap.outstanding:
        assert site.origin != "firmware", site.function


def test_nothing_was_freed_that_was_never_seen(memory: MemoryView) -> None:
    assert memory.heap.untracked_blocks == 0


def test_reading_it_twice_does_not_read_the_executable_twice(
    real_time_session: ProtobufSimulationSession,
) -> None:
    """Parsing it each time would take longer than the window measured."""
    definition = TomlBuildDefinitionRepository().load(DEFINITION)
    observe = ObserveMemory(real_time_session, DwarfDebugReader(), layout_of(definition))

    first = time.perf_counter()
    observe.execute()
    parsed = time.perf_counter() - first

    second = time.perf_counter()
    observe.execute()
    kept = time.perf_counter() - second

    assert kept < parsed


def test_the_audit_reports_the_same_static_memory(memory: MemoryView) -> None:
    """One number, read the same way whether a simulation is running.

    The firmware's own writable bytes: the figure the audit leads with,
    because looper's own recording rings are megabytes and are not on
    anybody's board.
    """
    from looper.presentation.cli.main import build_parser

    arguments = build_parser().parse_args(["audit", str(DEFINITION)])
    result = arguments.handler(arguments)

    assert memory.static.firmware_text in result.output


def test_a_definition_names_the_executable_that_was_read() -> None:
    definition = TomlBuildDefinitionRepository().load(DEFINITION)

    assert Path(definition.executable).is_file()
