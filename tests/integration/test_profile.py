"""Profiling a simulation that was really compiled and is really running.

Everything else about the profile can be tested with doubles. What
cannot is the part that has to be true of a real build: that the
compiler wove the hooks into the firmware and not into the runtime, that
the addresses the process reports map back onto the debug information
after relocation, and that the arithmetic holds on real measurements.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from conftest import DEFINITION

from looper.application.dto import ProfileView
from looper.application.queries import ObserveProfile
from looper.infrastructure.build import TomlBuildDefinitionRepository
from looper.infrastructure.debug import DwarfDebugReader
from looper.infrastructure.ipc import ProtobufSimulationSession
from looper.infrastructure.profile_layout import layout_of

WINDOW_SECONDS = 0.3


@pytest.fixture
def profile(real_time_session: ProtobufSimulationSession) -> ProfileView:
    """One window of profiling of the running example."""
    definition = TomlBuildDefinitionRepository().load(DEFINITION)
    observe = ObserveProfile(real_time_session, DwarfDebugReader(), layout_of(definition))
    observe.execute()
    observe.clear()
    time.sleep(WINDOW_SECONDS)
    return observe.execute()


def test_the_example_is_built_with_instrumentation(profile: ProfileView) -> None:
    assert profile.is_profiling, profile.note
    assert profile.function_count > 0


def test_the_addresses_are_resolved_into_names(profile: ProfileView) -> None:
    """An unresolved address keeps its number, so no name means no match."""
    names = _names(profile)

    assert names
    assert not [name for name in names if name.startswith("0x")]


def test_the_firmware_loop_was_measured(profile: ProfileView) -> None:
    assert "app_step" in _names(profile)


def test_the_runtime_is_not_woven_into_the_measurement(profile: ProfileView) -> None:
    """The apparatus must stay out of what it measures."""
    assert [group.label for group in profile.groups if group.label == "runtime"] == []


def test_the_generated_adapter_is_not_woven_either(profile: ProfileView) -> None:
    """It is already measured at its boundary, where it says more."""
    assert "adapter" not in [group.label for group in profile.groups]


def test_a_project_that_is_all_its_own_is_all_firmware(profile: ProfileView) -> None:
    """The example keeps its firmware and its model in one directory.

    There is nothing to separate them by, so nothing is separated. A
    project whose firmware lives elsewhere gets the two apart; see
    the unit tests of the layout for that.
    """
    assert [group.label for group in profile.groups] == ["firmware"]


def test_no_function_spent_more_in_itself_than_in_everything_it_called(
    profile: ProfileView,
) -> None:
    for entry in _entries(profile):
        assert entry.self_nanoseconds <= entry.total_nanoseconds, entry.name


def test_the_window_accounts_for_less_time_than_it_lasted(profile: ProfileView) -> None:
    """Uninstrumented code takes the rest; more than the window is a bug."""
    assert 0 < profile.measured_nanoseconds < WINDOW_SECONDS * 2e9


def test_nothing_was_dropped_for_want_of_room(profile: ProfileView) -> None:
    assert profile.lost_functions == 0


def test_every_function_was_compiled_from_somewhere_known(profile: ProfileView) -> None:
    for entry in _entries(profile):
        assert Path(entry.directory).is_dir(), entry.name


def _entries(profile: ProfileView) -> list[object]:
    """Every measured function the tree holds."""
    return [
        function.entry
        for group in profile.groups
        for directory in group.children
        for function in directory.children
        if function.entry is not None
    ]


def _names(profile: ProfileView) -> set[str]:
    """What every measured function is called."""
    return {entry.name for entry in _entries(profile)}  # type: ignore[attr-defined]
