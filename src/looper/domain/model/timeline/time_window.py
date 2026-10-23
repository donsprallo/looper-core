"""The stretch of time a view is looking at.

Everything a simulation records carries a moment, and every diagnostic
question about an order of events is asked of a stretch of them: this
second, that millisecond around the fault, the whole run. One value
object for that stretch, so that panning, zooming and clamping are
decided once and the same way for every lane -- a plot whose rows
disagree about which moment is on the left is worse than no plot.

Seconds rather than the microseconds the simulation records in: a
window is read by a person, and a person thinks in seconds. The
conversion happens once, where the recording is translated.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import inf, nextafter

#: The width a window is given when there is nothing to give it one --
#: a single moment, or a zoom that would otherwise collapse. A
#: microsecond, because that is the resolution the simulation records
#: at and nothing narrower is a view of anything.
#:
#: It is a wish rather than a rule. A run that has been going for days
#: is past the point where a float can tell one microsecond from the
#: next, and a window there is as narrow as the machine allows; see
#: `widened_end`.
SHORTEST_SECONDS = 1e-6


@dataclass(frozen=True)
class TimeWindow:
    """A span of time, from one moment to a later one.

    Attributes:
        start_seconds: Where the window begins.
        end_seconds: Where it ends, always after it begins.
    """

    start_seconds: float
    end_seconds: float

    def __post_init__(self) -> None:
        if self.end_seconds <= self.start_seconds:
            raise ValueError("A time window ends after it begins")

    @property
    def duration_seconds(self) -> float:
        """How long the window is."""
        return self.end_seconds - self.start_seconds

    @property
    def middle_seconds(self) -> float:
        """The moment halfway through it."""
        return self.start_seconds + self.duration_seconds / 2.0

    def holds(self, seconds: float) -> bool:
        """Whether a moment falls inside, the end counting as inside.

        Both ends belong to the window so that an event exactly on the
        boundary is drawn rather than lost between two views of it.
        """
        return self.start_seconds <= seconds <= self.end_seconds

    def overlaps(self, other: TimeWindow) -> bool:
        """Whether the two share any time at all."""
        return self.start_seconds <= other.end_seconds and other.start_seconds <= self.end_seconds

    def zoomed(self, factor: float, around_seconds: float | None = None) -> TimeWindow:
        """A window this many times as long, about a fixed moment.

        A factor below one narrows, above one widens. What stays put
        is the moment zoomed about -- the cursor, normally -- because
        a zoom that moves what you were looking at is a zoom you have
        to undo.

        Raises:
            ValueError: If the factor is not positive.
        """
        if factor <= 0.0:
            raise ValueError("A zoom factor is positive")
        anchor = self.middle_seconds if around_seconds is None else around_seconds
        start = anchor - (anchor - self.start_seconds) * factor
        return TimeWindow(start, widened_end(start, anchor + (self.end_seconds - anchor) * factor))

    def moved_by(self, seconds: float) -> TimeWindow:
        """The same window, later or earlier."""
        return TimeWindow(self.start_seconds + seconds, self.end_seconds + seconds)

    def clamped_to(self, bounds: TimeWindow) -> TimeWindow:
        """This window pushed inside another, keeping its length.

        Pushed rather than cut: panning off the end of a recording
        should stop at the end, not shrink what is on screen. A window
        longer than the bounds becomes the bounds, because there is
        nothing further to show.
        """
        if self.duration_seconds >= bounds.duration_seconds:
            return bounds
        shifted = min(max(self.start_seconds, bounds.start_seconds), _latest_start(self, bounds))
        return TimeWindow(shifted, shifted + self.duration_seconds)

    @classmethod
    def spanning(cls, moments: Iterable[float]) -> TimeWindow | None:
        """The window that just holds every one of these moments.

        Returns:
            The window, or nothing at all when there are no moments --
            which is not the same as a window of length zero, and the
            caller has to decide what to show instead.
        """
        gathered = sorted(moments)
        if not gathered:
            return None
        return cls(gathered[0], widened_end(gathered[0], gathered[-1]))


def widened_end(start_seconds: float, end_seconds: float) -> float:
    """An end a window can actually be built with.

    A single moment, or a zoom taken to its limit, leaves nothing
    between the two ends. The wish is a microsecond; what is always
    available is the next float, which is what keeps this honest on a
    recording that has been running long enough for a microsecond to
    be below the resolution of the number holding it.
    """
    return max(end_seconds, start_seconds + SHORTEST_SECONDS, nextafter(start_seconds, inf))


def _latest_start(window: TimeWindow, bounds: TimeWindow) -> float:
    """The furthest right this window may begin and still fit."""
    return bounds.end_seconds - window.duration_seconds
