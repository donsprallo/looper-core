"""Putting two instruments' measurements into one ranking.

The adapter boundary and the profiler each see half of a programme. The
thing that must not happen when they are shown together is a function
appearing twice, or a profiled function being drawn as one nothing
answers -- that marking means something, and it means nothing here.
"""

from __future__ import annotations

from looper.application.dto import (
    CallTimingView,
    ProfileEntryView,
    ProfileGroupView,
    ProfileView,
    TimingReportView,
)
from looper.application.mapping import merge_measured_functions


def a_boundary(*entries: CallTimingView) -> TimingReportView:
    """What the generated adapter measured of itself."""
    return TimingReportView(entries=entries)


def an_adapter_call(
    function: str, total_seconds: float, is_never_answered: bool = False
) -> CallTimingView:
    """One measurement from the adapter boundary."""
    return CallTimingView(
        function=function,
        calls=10,
        answered_calls=0 if is_never_answered else 10,
        total_seconds=total_seconds,
        mean="1.0 us",
        longest="2.0 us",
        is_never_answered=is_never_answered,
    )


def a_profile(*entries: ProfileEntryView) -> ProfileView:
    """A profile holding the given functions under one directory."""
    directory = ProfileGroupView(
        label="C:/fw/app/Src",
        children=tuple(
            ProfileGroupView(label=entry.name, calls=entry.calls, entry=entry) for entry in entries
        ),
    )
    return ProfileView(groups=(ProfileGroupView(label="firmware", children=(directory,)),))


def a_function(name: str, total_nanoseconds: int, origin: str = "firmware") -> ProfileEntryView:
    """One measurement from the profiler."""
    return ProfileEntryView(
        name=name,
        origin=origin,
        calls=20,
        total_nanoseconds=total_nanoseconds,
        self_nanoseconds=total_nanoseconds,
        mean_text="3.0 us",
        longest_text="9.0 us",
    )


def test_both_instruments_end_up_in_one_ranking() -> None:
    merged = merge_measured_functions(
        a_boundary(an_adapter_call("adapter_spi_transfer", 0.5)),
        a_profile(a_function("app_run", 1_000_000_000)),
    )

    assert [entry.function for entry in merged.entries] == ["app_run", "adapter_spi_transfer"]


def test_each_row_says_which_instrument_measured_it() -> None:
    merged = merge_measured_functions(
        a_boundary(an_adapter_call("adapter_spi_transfer", 0.5)),
        a_profile(a_function("app_run", 100), a_function("model_spi", 50, "device model")),
    )

    assert {entry.function: entry.origin for entry in merged.entries} == {
        "adapter_spi_transfer": "adapter",
        "app_run": "firmware",
        "model_spi": "device model",
    }


def test_a_profiled_function_is_never_marked_as_unanswered() -> None:
    """It ran, so the question the marking asks does not arise."""
    merged = merge_measured_functions(a_boundary(), a_profile(a_function("app_run", 100)))

    assert not merged.entries[0].is_never_answered
    assert merged.unanswered == ()


def test_an_unanswered_adapter_call_keeps_its_marking() -> None:
    merged = merge_measured_functions(
        a_boundary(an_adapter_call("adapter_spi_dma_is_busy", 0.1, is_never_answered=True)),
        a_profile(a_function("app_run", 100)),
    )

    assert [entry.function for entry in merged.unanswered] == ["adapter_spi_dma_is_busy"]


def test_a_client_without_a_profile_still_gets_the_adapter() -> None:
    merged = merge_measured_functions(
        a_boundary(an_adapter_call("adapter_spi_transfer", 0.5)), ProfileView()
    )

    assert [entry.function for entry in merged.entries] == ["adapter_spi_transfer"]


def test_the_profiled_numbers_come_through_as_they_are_shown() -> None:
    merged = merge_measured_functions(a_boundary(), a_profile(a_function("app_run", 100)))

    entry = merged.entries[0]
    assert (entry.calls, entry.mean, entry.longest) == (20, "3.0 us", "9.0 us")
