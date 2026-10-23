"""One thing that happened, at a moment or over a stretch.

The three recordings a simulation keeps -- values, bus exchanges and
adapter calls -- are different enough to deserve their own structures
and similar enough that a reader comparing them wants one shape: when
it happened, what it was, and anything worth reading beside it.

That shape is here. What it deliberately does not carry is how to draw
it. A mark is a mark whether it ends up a tick on a ruler, a row in a
table or a line in a report.
"""

from __future__ import annotations

from dataclasses import dataclass

from looper.domain.model.timeline.time_window import TimeWindow


@dataclass(frozen=True)
class TimelineEvent:
    """Something that happened, placed in time.

    Attributes:
        seconds: When it happened, or began.
        label: What it was, in as few words as carry meaning.
        detail: What is worth reading beside it -- a payload, a value,
            a reason. Empty when the label says everything.
        duration_seconds: How long it took. Zero for the ordinary case
            of a recording that knows when something happened and not
            how long it lasted.
    """

    seconds: float
    label: str
    detail: str = ""
    duration_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.seconds < 0.0:
            raise ValueError("An event happens at or after the start of the recording")
        if self.duration_seconds < 0.0:
            raise ValueError(f"'{self.label}' cannot last {self.duration_seconds} seconds")

    @property
    def end_seconds(self) -> float:
        """When it was over, which for an instant is when it began."""
        return self.seconds + self.duration_seconds

    @property
    def is_instant(self) -> bool:
        """Whether this is a moment rather than a stretch.

        The difference is what a drawing does with it: an instant is a
        tick and a stretch is a bar, and a bar of no width pretending
        to be a tick is a bar nobody can click on.
        """
        return self.duration_seconds == 0.0

    def falls_within(self, window: TimeWindow) -> bool:
        """Whether any part of it is inside the window.

        Any part, so that a stretch beginning before the window and
        ending inside it is drawn. A view that showed only events
        wholly inside would hide exactly the long ones, which are the
        ones worth looking at.
        """
        return window.holds(self.seconds) or window.holds(self.end_seconds) or self._spans(window)

    def _spans(self, window: TimeWindow) -> bool:
        """Whether it began before the window and ended after it."""
        return self.seconds <= window.start_seconds and self.end_seconds >= window.end_seconds
