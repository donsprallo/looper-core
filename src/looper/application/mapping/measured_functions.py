"""One ranking of everything that was measured, however it was measured.

Two instruments watch one programme. The generated adapter is timed at
its boundary, which is the only place that can also say whether anything
answered a call. Everything else is timed by the profiler the compiler
wove in. Neither sees what the other sees, and together they see the
whole of it.

So they are put in one list. Nothing is counted twice: the adapter is
deliberately left out of the instrumentation, so a function appears in
exactly one of the two.

What the list is not is a budget. A caller's time contains its callees',
so the bars overlap and adding them up means nothing -- which is already
true of the adapter alone, where the firmware's loop contains every call
it makes. The ranking is the point, and the profile page is where the
shares that do add up live.
"""

from __future__ import annotations

from looper.application.dto import (
    CallTimingView,
    ProfileEntryView,
    ProfileView,
    TimingReportView,
)

NANOSECONDS_PER_SECOND = 1_000_000_000


def merge_measured_functions(boundary: TimingReportView, profile: ProfileView) -> TimingReportView:
    """Rank the adapter boundary and the profile as one list.

    Args:
        boundary: What the generated adapter measured of itself.
        profile: What the profiler measured of everything else.

    Returns:
        Every measured function, heaviest first.
    """
    measured = [_as_timing(entry) for entry in _entries_of(profile)]
    together = [*boundary.entries, *measured]
    return TimingReportView(entries=tuple(sorted(together, key=lambda one: -one.total_seconds)))


def _as_timing(entry: ProfileEntryView) -> CallTimingView:
    """One profiled function, as the ranking shows it.

    A function the profiler saw run was carried out by definition, so
    every call of it counts as answered. The question the column asks --
    did anything stand behind this call -- is one only the adapter
    boundary can be asked.
    """
    return CallTimingView(
        function=entry.name,
        calls=entry.calls,
        answered_calls=entry.calls,
        total_seconds=entry.total_nanoseconds / NANOSECONDS_PER_SECOND,
        mean=entry.mean_text,
        longest=entry.longest_text,
        is_never_answered=False,
        origin=entry.origin,
    )


def _entries_of(profile: ProfileView) -> tuple[ProfileEntryView, ...]:
    """Every measured function the profile's tree holds."""
    return tuple(
        function.entry
        for group in profile.groups
        for directory in group.children
        for function in directory.children
        if function.entry is not None
    )
