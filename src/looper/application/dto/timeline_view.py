"""One ruler and its rows, ready to be drawn.

Two kinds of row reach a client, because two kinds of thing were
recorded. A curve is a measured value over time and is drawn as a
line; a lane is a list of things that happened and is drawn as marks.
Keeping them apart here is what lets the drawing stay simple -- a row
that was sometimes a line and sometimes a row of ticks would need a
branch at every step of the painting.

What they share is the window. That is the whole point of the page:
every row, whatever it is, is drawn against the same stretch of time.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator


class WindowView(BaseModel):
    """The stretch of time a page is showing.

    Attributes:
        start_seconds: Where the view begins.
        end_seconds: Where it ends.
    """

    model_config = ConfigDict(frozen=True)

    start_seconds: float
    end_seconds: float

    @property
    def duration_seconds(self) -> float:
        """How much time is on screen."""
        return self.end_seconds - self.start_seconds


class MarkView(BaseModel):
    """One thing that happened, as a row shows it.

    Attributes:
        seconds: When it happened, or began.
        duration_seconds: How long it lasted, zero for an instant.
        label: What it was.
        detail: What is worth reading beside it.
        is_doubtful: Whether something about it deserves attention --
            an exchange nothing took, a call nobody answered. Drawn
            differently, because those are what a reader is hunting.
        is_high: For a stretch on a digital row, whether the pin was
            high over it. Meaningless elsewhere and ignored there.
    """

    model_config = ConfigDict(frozen=True)

    seconds: float
    label: str
    detail: str = ""
    duration_seconds: float = 0.0
    is_doubtful: bool = False
    is_high: bool = False


class LaneView(BaseModel):
    """One row of marks.

    Attributes:
        key: What identifies the row between one reading and the next.
        label: What the row is called.
        kind: What it is a row of, which decides how it is drawn.
        marks: The ones carried in full, oldest first -- as many as a
            row can show apart, which on a busy bus is not all of them.
        count: How many times the watched thing did something, which
            is not how many marks there are.
        gaps: The gap before each occurrence, against when it ended,
            reduced to what a row can draw while keeping the longest
            and the shortest of each column. The one late arrival is
            the whole point of the plot, so it is what survives.
        usual_gap_seconds: The gap this row normally had, which is
            where the hairline under the spikes is drawn.
        worst_gap_seconds: The longest it ever waited, which is what
            the plot is scaled to.
        summary: How regular it was, in a few words, or empty when
            there was not enough of it to say.
    """

    model_config = ConfigDict(frozen=True)

    key: str
    label: str
    kind: str
    marks: tuple[MarkView, ...] = ()
    count: int = 0
    gaps: tuple[tuple[float, float], ...] = ()
    usual_gap_seconds: float = 0.0
    worst_gap_seconds: float = 0.0
    summary: str = ""

    @model_validator(mode="before")
    @classmethod
    def _counted_by_its_marks(cls, given: object) -> object:
        """Count the marks when a row carries all of what happened.

        Which is every row but a busy one. A caller that thinned its
        marks has to say how many there were, because the marks no
        longer say it; a caller that did not should not have to.
        """
        if not isinstance(given, dict) or given.get("count"):
            return given
        return {**given, "count": len(given.get("marks", ()))}

    @property
    def is_empty(self) -> bool:
        """Whether nothing happened on this row inside the window."""
        return self.count == 0


class CurveView(BaseModel):
    """One measured value over time.

    Attributes:
        key: What identifies the row between one reading and the next.
        label: What is being measured, with its unit.
        channel_id: Channel the points were recorded on.
        points: Time and value pairs, oldest first.
        lowest: Smallest value in the window.
        highest: Largest value in the window.
    """

    model_config = ConfigDict(frozen=True)

    key: str
    label: str
    channel_id: int
    points: tuple[tuple[float, float], ...] = ()
    lowest: float = 0.0
    highest: float = 0.0

    @property
    def is_empty(self) -> bool:
        """Whether this channel published nothing inside the window."""
        return not self.points


class TimelineView(BaseModel):
    """Everything a recording holds, on one stretch of time.

    Attributes:
        window: What is on screen.
        recorded: Everything there is to show, which is what a scroll
            bar is drawn against. Equal to the window when the whole
            recording fits on screen, and absent when nothing has been
            recorded at all.
        curves: The measured values, in channel order.
        lanes: The rows of marks, in reading order.
    """

    model_config = ConfigDict(frozen=True)

    window: WindowView
    recorded: WindowView | None = None
    curves: tuple[CurveView, ...] = ()
    lanes: tuple[LaneView, ...] = ()

    @property
    def is_empty(self) -> bool:
        """Whether there is nothing at all to draw."""
        return all(one.is_empty for one in self.curves) and all(one.is_empty for one in self.lanes)
