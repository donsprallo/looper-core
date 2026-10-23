"""The call tree of a simulation that was really compiled and is really running.

What doubles cannot check is the part that happens inside the
running process: that the hooks keep a node per path rather than per
function, that a caller's measurement really does contain its
callees', and that arming begins a window rather than handing over
whatever happened while nobody was following.

The tree is also the one recording that is off until it is asked
for, so the first thing checked is that an unarmed simulation says
so instead of reporting an empty window.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from conftest import DEFINITION

from looper.application.dto import FlameView
from looper.application.queries import ObserveFlame
from looper.infrastructure.build import TomlBuildDefinitionRepository
from looper.infrastructure.debug import DwarfDebugReader
from looper.infrastructure.ipc import ProtobufSimulationSession
from looper.infrastructure.profile_layout import layout_of

WINDOW_SECONDS = 0.3


@pytest.fixture
def observe(real_time_session: ProtobufSimulationSession) -> ObserveFlame:
    """The call tree of the running example, nobody following it yet."""
    definition = TomlBuildDefinitionRepository().load(DEFINITION)
    return ObserveFlame(real_time_session, DwarfDebugReader(), layout_of(definition))


@pytest.fixture
def flame(observe: ObserveFlame) -> FlameView:
    """One window of followed call paths."""
    observe.watch(True)
    time.sleep(WINDOW_SECONDS)
    return observe.execute()


def test_a_simulation_nobody_asked_says_so_rather_than_showing_nothing(
    observe: ObserveFlame,
) -> None:
    view = observe.execute()

    assert not view.is_watched
    assert view.is_empty


def test_the_firmware_loop_is_in_the_picture(flame: FlameView) -> None:
    assert "app_step" in {bar.name for bar in flame.frames}


def test_the_addresses_are_resolved_into_names(flame: FlameView) -> None:
    """An unresolved address keeps its number, so no name means no match."""
    assert flame.frames
    assert not [bar.name for bar in flame.frames if bar.name.startswith("0x")]


def test_a_callee_is_drawn_on_top_of_its_caller(flame: FlameView) -> None:
    """A tree of one row would mean the paths were never followed."""
    assert flame.depth > 1
    assert max(bar.depth for bar in flame.frames) > 0


def test_no_bar_is_wider_than_the_one_it_sits_on(flame: FlameView) -> None:
    """A caller's measurement contains its callees', or the picture lies."""
    widest_by_depth: dict[int, float] = {}
    for bar in flame.frames:
        widest_by_depth[bar.depth] = max(widest_by_depth.get(bar.depth, 0.0), bar.width)
    for depth, width in widest_by_depth.items():
        if depth > 0:
            assert width <= widest_by_depth[depth - 1] + 1e-9


def test_the_bars_of_one_row_do_not_overlap(flame: FlameView) -> None:
    """Side by side within their caller is the whole geometry."""
    for depth in {bar.depth for bar in flame.frames}:
        row = sorted((bar for bar in flame.frames if bar.depth == depth), key=lambda one: one.start)
        for before, after in zip(row, row[1:], strict=False):
            assert before.start + before.width <= after.start + 1e-9


def test_nothing_was_dropped_for_want_of_room(flame: FlameView) -> None:
    """The example reaches far fewer paths than the tree holds."""
    assert flame.note == ""


def test_arming_again_begins_a_new_window(observe: ObserveFlame) -> None:
    """What the calls did while nobody followed them is of no use."""
    observe.watch(True)
    time.sleep(WINDOW_SECONDS)
    first = observe.execute()
    observe.watch(False)
    observe.watch(True)
    second = observe.execute()

    assert _nanoseconds(second) < _nanoseconds(first)


def test_what_is_followed_is_also_in_the_ranking(flame: FlameView) -> None:
    """Both instruments are the same hooks; a name in one is a name in both."""
    assert {bar.name for bar in flame.frames} <= set(_instrumented())


def _instrumented() -> set[str]:
    """Every function the example was woven with, by name."""
    definition = TomlBuildDefinitionRepository().load(DEFINITION)
    executable = Path(definition.executable)
    return {symbol.name for symbol in DwarfDebugReader().read_functions(executable)}


def _nanoseconds(view: FlameView) -> float:
    """How much host time one window accounts for, as a number."""
    scale = {"ns": 1.0, "us": 1e3, "ms": 1e6, "s": 1e9}
    amount, unit = view.total.split(" ") if view.total else ("0", "ns")
    return float(amount) * scale[unit]
