"""Mapping of the adapter boundary measurements onto the client facing views."""

from __future__ import annotations

from looper.application.dto.timing_view import CallTimingView, TimingReportView
from looper.domain.model.measurement import Distribution
from looper.domain.model.simulation import CallTiming

#: The share a quoted upper bound covers. Not the worst case, which
#: one unlucky call owns; this is what the call takes when nothing
#: unusual happens, and the gap between the two is the finding.
TYPICAL_SHARE = 0.95

#: Said of a function whose calls fall into separated groups.
SPLIT = "two paths"


def build_timing_report_view(timings: tuple[CallTiming, ...]) -> TimingReportView:
    """Translate the measurements into a report, heaviest first.

    Ordered by the host time spent rather than by name, because the first
    question a measurement answers is where the time went.
    """
    ordered = sorted(timings, key=lambda timing: -timing.total_nanoseconds)
    return TimingReportView(entries=tuple(_build_entry(timing) for timing in ordered))


def _build_entry(timing: CallTiming) -> CallTimingView:
    """Translate one function's measurements into its view."""
    return CallTimingView(
        function=timing.function,
        calls=timing.calls,
        answered_calls=timing.answered_calls,
        total_seconds=timing.total_seconds,
        mean=timing.display_mean,
        longest=timing.display_longest,
        is_never_answered=timing.is_never_answered,
        bands=timing.spread.counts,
        shape=_shape_text(timing.spread),
    )


def _shape_text(spread: Distribution) -> str:
    """What the spread amounts to, in the words a column has room for.

    Two separated groups are worth saying out loud, because that is
    two paths through the code rather than one with variation, and
    the question then becomes which one is taken when.
    """
    if not spread.is_measured:
        return ""
    typical = _duration(spread.at_most_seconds(TYPICAL_SHARE))
    if spread.is_split:
        return f"{SPLIT}, 95% under {typical}"
    return f"95% under {typical}"


def _duration(seconds: float) -> str:
    """A length of time as a person reads it."""
    if seconds < 1e-6:
        return f"{seconds * 1e9:.0f} ns"
    if seconds < 1e-3:
        return f"{seconds * 1e6:.1f} us"
    if seconds < 1.0:
        return f"{seconds * 1e3:.1f} ms"
    return f"{seconds:.2f} s"
