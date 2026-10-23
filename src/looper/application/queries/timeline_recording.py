"""What a client has collected of the four recordings, so far.

Each recording in the simulation is a ring it overwrites as it goes,
and a reply carries a page of one. A client that only ever showed the
latest reply would show a few milliseconds of a run; what a reader
wants is the last few seconds, assembled from however many replies
that took. So the pages are kept here, and what falls out of the
window is dropped rather than held for ever -- a page nobody closed
should not grow without end.

Reading is kept apart from arranging. This gathers; `ObserveTimeline`
decides what the rows are and what they are called.

Two of the four recordings are read by the rest of the window as well --
the scope plots the measured values and the bus table lists the
exchanges -- and a page of either costs more to decode than everything
this page does with it. So they can be handed in by whoever read them,
and only the journal and the pin trace, which nobody else reads, are
read here.

When each thing happened is kept beside the thing itself. It is the same
number read off the same record, but a window holds tens of thousands of
them and how regular a row was is measured from all of them on every
reading -- so it is worth not walking the records again to collect
numbers that were there when they arrived.
"""

from __future__ import annotations

from collections import defaultdict, deque

from looper.application.dto.analog_view import TraceView
from looper.application.dto.bus_view import BusTraceView, ExchangeView
from looper.application.queries.observe_analog import MAXIMUM_PAGES, ReadTrace
from looper.application.queries.observe_buses import ReadBusTrace
from looper.domain.model.simulation import AdapterCall, PinChange
from looper.domain.ports import SimulationSession

#: Points one curve keeps, however fast the firmware publishes. A
#: window of five seconds at sixteen thousand samples a second is far
#: more than a screen can show, and the decimation that draws it reads
#: every one of them.
MAXIMUM_POINTS = 20_000


class TimelineRecording:
    """Everything read so far, bounded by the window it is shown in."""

    def __init__(self, session: SimulationSession) -> None:
        self._session = session
        self._trace = ReadTrace(session)
        self._bus_trace = ReadBusTrace(session)
        self.curves: dict[int, deque[tuple[float, float]]] = defaultdict(deque)
        self.exchanges: dict[int, deque[ExchangeView]] = defaultdict(deque)
        self.exchange_moments: dict[int, deque[float]] = defaultdict(deque)
        self.calls: dict[str, deque[AdapterCall]] = defaultdict(deque)
        self.call_moments: dict[str, deque[float]] = defaultdict(deque)
        self.pins: dict[int, deque[PinChange]] = defaultdict(deque)
        self.calls_are_complete = True
        self.latest_seconds = 0.0
        self._sample_position = 0
        self._exchange_position = 0
        self._pin_position = 0
        self._call_sequence = -1

    def clear(self) -> None:
        """Forget everything read so far and start again."""
        self.curves.clear()
        self.exchanges.clear()
        self.exchange_moments.clear()
        self.calls.clear()
        self.call_moments.clear()
        self.pins.clear()
        self.calls_are_complete = True
        self.latest_seconds = 0.0
        self._sample_position = 0
        self._exchange_position = 0
        self._pin_position = 0
        self._call_sequence = -1

    def take_everything(self) -> None:
        """Read whatever is new in all four recordings."""
        self.take_samples(self._trace.execute(self._sample_position))
        self.take_exchanges(self._bus_trace.execute(self._exchange_position))
        self.take_its_own()

    def take_its_own(self) -> None:
        """Read the two recordings nobody else reads.

        The journal and the pin trace are read by this page and by
        nothing else, so there is never a page of them in somebody
        else's hands to be given instead.
        """
        self._take_calls()
        self._take_pin_changes()

    def take_samples(self, trace: TraceView) -> None:
        """Keep a page of measured values somebody has already read.

        Only what is newer than what is held. A page can arrive from
        two places -- the poll that reads for the scope, and the one
        catching-up read when the tab is opened -- and each counts
        from where it had got to, so the two overlap.
        """
        for sample in trace.samples:
            if sample.sequence < self._sample_position:
                continue
            self.curves[sample.channel_id].append((sample.seconds, sample.value))
            self.latest_seconds = max(self.latest_seconds, sample.seconds)
        self._sample_position = max(self._sample_position, trace.next_sequence)

    def take_exchanges(self, trace: BusTraceView) -> None:
        """Keep a page of bus exchanges somebody has already read.

        Only what is newer than what is held, for the same reason
        the samples are: two readers, each counting from its own
        place, hand over stretches that overlap.
        """
        for exchange in trace.exchanges:
            if exchange.sequence < self._exchange_position:
                continue
            self.exchanges[exchange.bus_id].append(exchange)
            self.exchange_moments[exchange.bus_id].append(exchange.seconds)
            self.latest_seconds = max(self.latest_seconds, exchange.seconds)
        self._exchange_position = max(self._exchange_position, trace.next_sequence)

    def forget_before(self, oldest: float) -> None:
        """Drop everything older than a moment.

        From the front, one at a time, because that is how many
        there are to drop. Rebuilding each list around what survives
        costs the whole window on every poll, and the whole window
        is tens of thousands of exchanges on a busy bus.
        """
        for points in self.curves.values():
            while points and (points[0][0] < oldest or len(points) > MAXIMUM_POINTS):
                points.popleft()
        for bus, exchanges in self.exchanges.items():
            while exchanges and exchanges[0].seconds < oldest:
                exchanges.popleft()
                self.exchange_moments[bus].popleft()
        for peripheral, calls in self.calls.items():
            while calls and calls[0].seconds < oldest:
                calls.popleft()
                self.call_moments[peripheral].popleft()
        for changes in self.pins.values():
            _forget_old_changes(changes, oldest)

    def _take_calls(self) -> None:
        """Read the adapter calls the journal still holds.

        By sequence rather than by what the reply contains: the
        journal hands over its most recent page every time, so most
        of what arrives has already been seen -- and when the
        firmware called faster than this read, some of it never will
        be. A gap in the numbering is how that is noticed.
        """
        recorded = self._session.read_journal()
        if self._skipped_calls(recorded):
            self.calls_are_complete = False
        for call in recorded:
            if call.sequence <= self._call_sequence:
                continue
            self._call_sequence = call.sequence
            self.calls[call.peripheral].append(call)
            self.call_moments[call.peripheral].append(call.seconds)
            self.latest_seconds = max(self.latest_seconds, call.seconds)

    def _skipped_calls(self, recorded: tuple[AdapterCall, ...]) -> bool:
        """Whether calls happened that this reading will never see.

        Not on the first reading: what the journal had already
        forgotten before anybody looked is not a gap in the view.
        """
        if not recorded or self._call_sequence < 0:
            return False
        return recorded[0].sequence > self._call_sequence + 1

    def _take_pin_changes(self) -> None:
        """Read the level changes recorded since the last reading."""
        for _ in range(MAXIMUM_PAGES):
            changes, recorded = self._session.read_pin_trace(self._pin_position)
            if not changes:
                break
            for change in changes:
                self.pins[change.pin].append(change)
                self.latest_seconds = max(self.latest_seconds, change.seconds)
            self._pin_position = changes[-1].sequence + 1
            if self._pin_position >= recorded:
                break


def _forget_old_changes(changes: deque[PinChange], oldest: float) -> None:
    """Drop old changes, keeping the one the window opens at.

    One more than the window needs: the level a pin held when the
    window opened was set by a change before it, and dropping that
    would leave the row blank until the pin next moved.
    """
    while len(changes) > 1 and changes[1].seconds < oldest:
        changes.popleft()
