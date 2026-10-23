"""Translation of a profile into something a client can draw."""

from __future__ import annotations

from looper.application.dto import ProfileEntryView, ProfileGroupView, ProfileView
from looper.domain.model.profile import ProfiledFunction, ProfileGroup, ProfileReport
from looper.domain.model.simulation.duration import duration_text

#: How many functions a summary names before a reader stops reading.
HEAVIEST_SHOWN = 12


def build_profile_view(report: ProfileReport, is_profiling: bool) -> ProfileView:
    """Describe a whole window of profiling."""
    measured = report.measured_nanoseconds
    return ProfileView(
        groups=tuple(_group_view(group, measured) for group in report.by_origin()),
        heaviest=tuple(_entry_view(one) for one in report.heaviest(HEAVIEST_SHOWN)),
        measured_nanoseconds=measured,
        measured_text=duration_text(float(measured)),
        lost_functions=report.lost_functions,
        is_profiling=is_profiling,
    )


def _group_view(group: ProfileGroup, measured_nanoseconds: int) -> ProfileGroupView:
    """Describe one group and everything under it."""
    return ProfileGroupView(
        label=group.label,
        calls=group.calls,
        self_nanoseconds=group.self_nanoseconds,
        self_text=group.display_self,
        share=group.share_of(measured_nanoseconds),
        children=tuple(_group_view(child, measured_nanoseconds) for child in group.children),
        entry=_entry_view(group.function) if group.function is not None else None,
    )


def _entry_view(function: ProfiledFunction) -> ProfileEntryView:
    """Describe one measured function."""
    return ProfileEntryView(
        name=function.name,
        origin=function.origin.value,
        directory=function.directory,
        file_name=function.file_name,
        calls=function.calls,
        self_nanoseconds=function.self_nanoseconds,
        total_nanoseconds=function.total_nanoseconds,
        self_text=function.display_self,
        total_text=function.display_total,
        mean_text=function.display_mean,
        longest_text=duration_text(float(function.longest_nanoseconds)),
    )
