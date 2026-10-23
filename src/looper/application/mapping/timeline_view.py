"""Turning three recordings into the rows of one ruler.

The arranging is the work. Each recording already carries moments on
the same clock; what it does not carry is which row it belongs on, or
what a reader should see written beside it. A bus exchange belongs to
its bus, an adapter call to its peripheral, and both want a label
short enough to fit under a mark and a detail long enough to be worth
hovering over.

The domain decides what a lane is and what a window shows. This
decides what the rows are called -- and how much of a row is worth
carrying, which is the other half of the job. A bus exchanging seven
thousand times a second fills a five second window with thirty five
thousand marks, and a row is a thousand pixels wide. Carrying them
all cost a third of a second per reading and drew thirty marks on
every pixel.

So a row carries every moment, which is a number and is what its
regularity is measured from, and a mark for as many of them as can
be told apart. The summary says how many there really were.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from looper.application.dto.bus_view import ExchangeView
from looper.application.dto.timeline_view import LaneView, MarkView, WindowView
from looper.domain.model.simulation import AdapterCall
from looper.domain.model.timeline import LaneKind, TimelineEvent, TimelineLane, TimeWindow
from looper.domain.services import Cadence, LevelRun, cadence_of, decimate

#: What a mark says when an exchange carried nothing.
EMPTY_PAYLOAD = "(no bytes)"

#: Said of an exchange nothing on the bus took.
REFUSED = "nothing took it"

#: What a stretch at each level is called.
HIGH = "high"
LOW = "low"

#: Said of a row that is missing some of what happened. The journal
#: is a short ring and one reply carries part of it, so a firmware
#: calling faster than the page reads leaves holes -- and a period
#: measured across a hole is a reading of the hole.
SAMPLED = "sampled, gaps not shown"

#: Columns the jitter plot is reduced to, for the same reason the
#: marks are: it is drawn across a row, and a row has pixels. Each
#: column keeps its longest and its shortest gap, so the one late
#: arrival the plot exists for is never the one dropped.
CADENCE_COLUMNS = 1_000

#: Marks one row carries in full. About what a wide row has pixels:
#: a tick is a hairline, so beyond one per pixel they are drawn on
#: top of each other whatever is kept, and the row says how many
#: there really were.
MAXIMUM_MARKS = 1_000


def build_window_view(window: TimeWindow) -> WindowView:
    """Hand a stretch of time to a client."""
    return WindowView(start_seconds=window.start_seconds, end_seconds=window.end_seconds)


def bus_lane(
    key: str, label: str, exchanges: Sequence[ExchangeView], moments: Sequence[float]
) -> TimelineLane:
    """One bus and everything that crossed it."""
    return TimelineLane(
        key=key,
        label=label,
        kind=LaneKind.BUS,
        events=tuple(_exchange_event(one) for one in thinned(exchanges)),
        moments=tuple(moments),
    )


def call_lane(
    key: str, label: str, calls: Sequence[AdapterCall], moments: Sequence[float]
) -> TimelineLane:
    """One peripheral and the calls the firmware made into it."""
    return TimelineLane(
        key=key,
        label=label,
        kind=LaneKind.CALL,
        events=tuple(
            TimelineEvent(seconds=one.seconds, label=one.function) for one in thinned(calls)
        ),
        moments=tuple(moments),
    )


def thinned[Thing](happenings: Sequence[Thing], limit: int = MAXIMUM_MARKS) -> Sequence[Thing]:
    """As many of them as are worth carrying, evenly spread.

    Evenly rather than the newest, because a row is read across its
    whole width: keeping the last two thousand of a busy second would
    draw a dense block on the right and leave the rest of the window
    blank, which is a picture of the thinning rather than of the bus.

    The first and the last are always kept, so that a row still
    begins and ends where its traffic did.
    """
    held = len(happenings)
    if held <= limit:
        return happenings
    stride = held / limit
    kept = [happenings[int(index * stride)] for index in range(limit)]
    kept[-1] = happenings[-1]
    return kept


def pin_lane(key: str, label: str, runs: Sequence[LevelRun]) -> TimelineLane:
    """One pin and the stretches it spent at a level.

    Stretches rather than moments, because that is what a logic
    analyser draws and what a reader asks of it: not "it changed at
    1.2 s" but "it was low from 1.2 to 1.9".
    """
    return TimelineLane(
        key=key,
        label=label,
        kind=LaneKind.DIGITAL,
        events=tuple(_run_event(one) for one in runs),
    )


def _run_event(run: LevelRun) -> TimelineEvent:
    """One stretch at one level."""
    return TimelineEvent(
        seconds=run.start_seconds,
        label=HIGH if run.is_high else LOW,
        detail=_duration(run.duration_seconds),
        duration_seconds=run.duration_seconds,
    )


def build_lane_view(lane: TimelineLane, window: TimeWindow, is_complete: bool = True) -> LaneView:
    """Hand one row to a client: its marks, and how regular it was.

    The regularity is measured here, from every moment the row had,
    rather than handed over as moments for a drawing to measure. A
    busy bus has tens of thousands of them per window and a row has
    a thousand pixels; shipping them all meant counting the same
    gaps again on every repaint.

    A row that is missing some of what happened gets no cadence. The
    gaps would be the reader's own blind spots rather than the
    firmware's, and a worst case measured across one of them is the
    most confident wrong number a page could print.
    """
    cadence = cadence_of(lane.moments)
    return LaneView(
        key=lane.key,
        label=lane.label,
        kind=lane.kind.value,
        marks=tuple(_mark_view(one) for one in lane.events),
        count=len(lane.moments),
        gaps=_drawable_gaps(lane, cadence, window),
        usual_gap_seconds=cadence.median_seconds,
        worst_gap_seconds=cadence.longest_seconds,
        summary=SAMPLED if not is_complete else _summary_of(cadence),
    )


def _drawable_gaps(
    lane: TimelineLane, cadence: Cadence, window: TimeWindow
) -> tuple[tuple[float, float], ...]:
    """Every gap against when it ended, reduced to what a row draws."""
    if not cadence.is_measured:
        return ()
    against_time = list(zip(lane.moments[1:], cadence.intervals, strict=True))
    reduced = decimate(against_time, window.start_seconds, window.duration_seconds, CADENCE_COLUMNS)
    return tuple(reduced)


def cadence_summary(moments: Iterable[float]) -> str:
    """How regular a row was, in the few words a header has room for."""
    return _summary_of(cadence_of(tuple(moments)))


def _summary_of(cadence: Cadence) -> str:
    """The same, said of a cadence already worked out.

    The median rather than the mean, and the worst gap beside it: one
    late occurrence drags a mean and hides in it, and the worst gap is
    the number a deadline is judged against.
    """
    if not cadence.is_measured:
        return ""
    return (
        f"{cadence.count + 1}x, every {_duration(cadence.median_seconds)}, "
        f"worst {_duration(cadence.longest_seconds)}"
    )


def _exchange_event(exchange: ExchangeView) -> TimelineEvent:
    """One exchange as something that happened at a moment."""
    return TimelineEvent(
        seconds=exchange.seconds,
        label=exchange.address,
        detail=_exchange_detail(exchange),
    )


def _exchange_detail(exchange: ExchangeView) -> str:
    """What is worth reading beside an exchange."""
    carried = exchange.payload or EMPTY_PAYLOAD
    if exchange.response:
        carried = f"{carried} -> {exchange.response}"
    if exchange.was_refused:
        return f"{carried}  [{REFUSED}]"
    return carried


def _mark_view(event: TimelineEvent) -> MarkView:
    """One event as a client draws it."""
    return MarkView(
        seconds=event.seconds,
        label=event.label,
        detail=event.detail,
        duration_seconds=event.duration_seconds,
        is_doubtful=REFUSED in event.detail,
        is_high=event.label == HIGH,
    )


def _duration(seconds: float) -> str:
    """A length of time as a person reads it."""
    if seconds < 1e-3:
        return f"{seconds * 1e6:.0f} us"
    if seconds < 1.0:
        return f"{seconds * 1e3:.1f} ms"
    return f"{seconds:.2f} s"
