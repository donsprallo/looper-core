"""One row of the ruler, and what it is a row of.

A lane is one thing being watched over time: a pin, a bus, a group of
adapter calls, an analog channel. Keeping the kind on the lane rather
than on each event is what lets a drawing decide once how a row is
rendered -- levels as a band, exchanges as arrows, calls as ticks --
instead of asking every mark what it would like to be.

A lane holds two things, and the difference between them is the
difference between what happened and what is worth drawing. The
moments are every time the watched thing did something: bare numbers,
all of them, which is what the regularity of a row is measured from.
The events are the ones carried in full, with a label and a detail,
and there is no use in more of those than a row has room for -- a bus
exchanging seven thousand times a second fills a five second window
with marks a thousand to the pixel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from looper.domain.model.timeline.event import TimelineEvent
from looper.domain.model.timeline.time_window import TimeWindow


class LaneKind(Enum):
    """What a row is a row of.

    Attributes:
        ANALOG: A measured value, drawn as a curve.
        DIGITAL: A level that is high or low, drawn as a band.
        BUS: Exchanges between two participants, drawn as arrows.
        CALL: Adapter calls, drawn as ticks or bars.
        STATE: A named state the firmware was in, drawn as a band.
    """

    ANALOG = "analog"
    DIGITAL = "digital"
    BUS = "bus"
    CALL = "call"
    STATE = "state"


@dataclass(frozen=True)
class TimelineLane:
    """One watched thing and everything it did.

    Attributes:
        key: What identifies the row between one reading and the next,
            so that a row the reader opened or hid stays that way.
        label: What the row is called.
        kind: What it is a row of.
        events: What is carried in full, oldest first.
        moments: When the watched thing did something, oldest first.
            Taken from the events when it is not given, which is what
            a lane small enough to carry whole wants.
    """

    key: str
    label: str
    kind: LaneKind
    events: tuple[TimelineEvent, ...] = field(default_factory=tuple)
    moments: tuple[float, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("A lane is identified by a key")
        if not self.moments and self.events:
            object.__setattr__(self, "moments", tuple(one.seconds for one in self.events))
        if _out_of_order(self.moments):
            raise ValueError(f"The events of '{self.key}' are not in order")

    @property
    def is_empty(self) -> bool:
        """Whether nothing happened on this lane at all.

        Worth keeping apart from a lane that does not exist: a bus
        with no traffic is a finding, and a bus nobody wired up is a
        different one.
        """
        return not self.moments

    @property
    def is_thinned(self) -> bool:
        """Whether more happened here than the lane carries in full."""
        return len(self.events) < len(self.moments)

    def within(self, window: TimeWindow) -> TimelineLane:
        """The same lane holding only what the window shows.

        The two are filtered by their own rules, which is why they
        can come out of different lengths. A stretch that began
        before the window and reaches into it is still drawn, because
        the long ones are the ones worth looking at; the moment it
        began is nonetheless not a moment inside the window.
        """
        return TimelineLane(
            key=self.key,
            label=self.label,
            kind=self.kind,
            events=tuple(event for event in self.events if event.falls_within(window)),
            moments=tuple(one for one in self.moments if window.holds(one)),
        )


def _out_of_order(moments: tuple[float, ...]) -> bool:
    """Whether a later moment comes before an earlier one.

    Checked on every lane of every reading, so it walks the numbers
    rather than building the pairs it walks.
    """
    return any(later < earlier for earlier, later in zip(moments, moments[1:], strict=False))
