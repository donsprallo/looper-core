"""Use case that reads what the adapter boundary cost."""

from __future__ import annotations

from looper.application.dto.timing_view import TimingReportView
from looper.application.mapping.timing_view import build_timing_report_view
from looper.domain.ports import SimulationSession


class ObserveCallTimings:
    """Reads how often each adapter call was made and what it cost.

    Two questions at once. Where the simulation spends itself, which is the
    host time; and what it is pretending, which is the difference between
    the calls made and the ones anything answered.
    """

    def __init__(self, session: SimulationSession) -> None:
        self._session = session

    def execute(self) -> TimingReportView:
        """Take one snapshot of the measurements."""
        return build_timing_report_view(self._session.read_call_timings())

    def clear(self) -> None:
        """Forget the measurements and start again."""
        self._session.clear_call_timings()
