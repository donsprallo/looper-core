"""How a profile adds up, and what it refuses to add up.

The one arithmetic rule worth defending is that totals overlap and self
times do not. A report that summed totals would say a firmware spent
four seconds in one, and would be believed once.
"""

from __future__ import annotations

from pathlib import PurePath

import pytest

from looper.domain.model.profile import ProfiledFunction, ProfileReport
from looper.domain.model.sources import FunctionOrigin, SourceLayout

APP = PurePath("C:/fw/app/Src/app.c")
MODEL = PurePath("C:/project/src/board.c")


def a_function(
    name: str,
    self_nanoseconds: int,
    total_nanoseconds: int | None = None,
    source: PurePath = APP,
    origin: FunctionOrigin = FunctionOrigin.FIRMWARE,
    calls: int = 1,
) -> ProfiledFunction:
    """One measured function, named only by what a test is about."""
    return ProfiledFunction(
        name=name,
        origin=origin,
        source=source,
        calls=calls,
        total_nanoseconds=(
            total_nanoseconds if total_nanoseconds is not None else self_nanoseconds
        ),
        self_nanoseconds=self_nanoseconds,
    )


def test_what_a_function_spent_in_its_callees_is_the_difference() -> None:
    caller = a_function("app_run", self_nanoseconds=300, total_nanoseconds=1000)

    assert caller.children_nanoseconds == 700


def test_a_function_cannot_spend_more_in_itself_than_in_everything() -> None:
    with pytest.raises(ValueError, match="more time in itself"):
        ProfiledFunction(
            name="app_run",
            origin=FunctionOrigin.FIRMWARE,
            total_nanoseconds=100,
            self_nanoseconds=200,
        )


def test_the_measured_window_is_the_sum_of_self_times_and_not_of_totals() -> None:
    """A caller's total already holds its callees', so only self times add."""
    report = ProfileReport(
        functions=(
            a_function("app_run", self_nanoseconds=300, total_nanoseconds=1000),
            a_function("app_step", self_nanoseconds=700),
        )
    )

    assert report.measured_nanoseconds == 1000


def test_the_tree_is_origin_then_directory_then_function() -> None:
    report = ProfileReport(
        functions=(
            a_function("app_run", 300),
            a_function("model_spi", 100, source=MODEL, origin=FunctionOrigin.DEVICE_MODEL),
        )
    )

    firmware, model = report.by_origin()

    assert (firmware.label, firmware.self_nanoseconds) == ("firmware", 300)
    assert firmware.children[0].label == str(APP.parent)
    assert firmware.children[0].children[0].label == "app_run"
    assert model.label == "device model"


def test_every_level_is_heaviest_first() -> None:
    report = ProfileReport(
        functions=(a_function("light", 10), a_function("heavy", 90)),
    )

    functions = report.by_origin()[0].children[0].children

    assert [one.label for one in functions] == ["heavy", "light"]


def test_a_group_says_what_part_of_the_window_it_accounts_for() -> None:
    report = ProfileReport(
        functions=(
            a_function("app_run", 750),
            a_function("model_spi", 250, source=MODEL, origin=FunctionOrigin.DEVICE_MODEL),
        )
    )

    firmware = report.by_origin()[0]

    assert firmware.share_of(report.measured_nanoseconds) == pytest.approx(0.75)


def test_a_share_of_nothing_is_nothing_rather_than_an_error() -> None:
    report = ProfileReport(functions=(a_function("app_run", 0),))

    assert report.by_origin()[0].share_of(report.measured_nanoseconds) == 0.0


def test_the_heaviest_are_the_ones_that_spent_the_time_in_themselves() -> None:
    report = ProfileReport(
        functions=(
            a_function("conductor", self_nanoseconds=10, total_nanoseconds=900),
            a_function("worker", self_nanoseconds=500),
        )
    )

    assert [one.name for one in report.heaviest(1)] == ["worker"]


def test_a_dropped_measurement_is_carried_rather_than_hidden() -> None:
    assert ProfileReport(lost_functions=7).lost_functions == 7
    with pytest.raises(ValueError, match="negative"):
        ProfileReport(lost_functions=-1)


def test_a_function_with_no_source_came_out_of_a_library() -> None:
    layout = SourceLayout(firmware=(PurePath("C:/fw"),))

    assert layout.origin_of(None) is FunctionOrigin.LIBRARY


def test_a_source_no_directory_claims_was_still_compiled_here() -> None:
    """Debug information means it was built here, so it is not a library."""
    layout = SourceLayout(runtime=(PurePath("C:/looper/runtime"),))

    assert layout.origin_of(PurePath("C:/elsewhere/thing.c")) is FunctionOrigin.FIRMWARE


def test_the_narrower_claim_wins_over_the_wider_one() -> None:
    """The generated adapter sits inside the project that owns the model."""
    layout = SourceLayout(
        adapter=(PurePath("C:/project/build/generated"),),
        device_model=(PurePath("C:/project"),),
    )

    generated = PurePath("C:/project/build/generated/sil_adapter_spi.c")
    assert layout.origin_of(generated) is FunctionOrigin.ADAPTER
    assert layout.origin_of(PurePath("C:/project/src/board.c")) is FunctionOrigin.DEVICE_MODEL


def test_a_path_spelled_in_another_case_is_the_same_path() -> None:
    layout = SourceLayout(runtime=(PurePath("C:/Looper/Runtime"),))

    assert layout.origin_of(PurePath("c:/looper/runtime/src/x.c")) is FunctionOrigin.RUNTIME


def test_asking_twice_about_one_file_gives_one_answer() -> None:
    """The answer is kept, because a profile asks hundreds of times a second."""
    layout = SourceLayout(runtime=(PurePath("C:/looper/runtime"),))
    source = PurePath("C:/looper/runtime/src/clock.c")

    assert layout.origin_of(source) is layout.origin_of(source)
    assert layout.origin_of(source) is FunctionOrigin.RUNTIME


def test_what_one_layout_worked_out_is_not_another_layouts_answer() -> None:
    """Two layouts claim different directories and must not share a memory."""
    source = PurePath("C:/project/src/board.c")
    model = SourceLayout(device_model=(PurePath("C:/project/src"),))
    runtime = SourceLayout(runtime=(PurePath("C:/project/src"),))

    assert model.origin_of(source) is FunctionOrigin.DEVICE_MODEL
    assert runtime.origin_of(source) is FunctionOrigin.RUNTIME


def test_two_layouts_that_claim_the_same_directories_are_the_same_layout() -> None:
    """What is worked out along the way is not part of what one is."""
    directories = (PurePath("C:/fw"),)

    first = SourceLayout(firmware=directories)
    second = SourceLayout(firmware=directories)
    first.origin_of(PurePath("C:/fw/app.c"))

    assert first == second
