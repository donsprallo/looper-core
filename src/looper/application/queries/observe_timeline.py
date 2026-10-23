"""Everything the simulation records, on one stretch of time.

Four recordings carry moments from the same clock -- measured values,
pin levels, bus exchanges and adapter calls -- and until now they
were read in four places and compared by hand. Putting them on one
ruler answers the question none of them answers alone: in what order
did this happen, and what happened at the same time as what.

What is here is the arranging. The gathering is in
`TimelineRecording`, because keeping pages of four rings is a job of
its own and has nothing to say about what the rows are called.
"""

from __future__ import annotations

from looper.application.dto.analog_view import ChannelView, TraceView
from looper.application.dto.bus_view import BusTraceView, BusView
from looper.application.dto.timeline_view import CurveView, LaneView, TimelineView
from looper.application.mapping.analog_view import build_channel_view
from looper.application.mapping.bus_view import build_bus_view
from looper.application.mapping.timeline_view import (
    build_lane_view,
    build_window_view,
    bus_lane,
    call_lane,
    pin_lane,
)
from looper.application.queries.timeline_recording import TimelineRecording
from looper.domain.model.simulation import GpioPinState
from looper.domain.model.timeline import LaneKind, Timeline, TimelineLane, TimeWindow
from looper.domain.ports import SimulationSession
from looper.domain.services import decimate, runs_of, value_range

#: How much of the past a page shows until it is told otherwise.
DEFAULT_WINDOW_SECONDS = 5.0

#: Columns a curve is reduced to before it is handed over. A window
#: five seconds long holds forty thousand samples of a converter at
#: eight kilohertz, and no drawing of it is a thousand pixels wider
#: than this. Each column keeps the lowest and the highest value
#: that fell in it, so a spike between two columns survives.
CURVE_COLUMNS = 1_000


class ObserveTimeline:
    """Assembles one ruler out of everything that was recorded.

    Stateful on purpose. The recordings are rings and the replies are
    pages, so the only place that can hold a window of several
    seconds is the thing doing the reading.
    """

    def __init__(
        self, session: SimulationSession, window_seconds: float = DEFAULT_WINDOW_SECONDS
    ) -> None:
        self._session = session
        self._recording = TimelineRecording(session)
        self._window_seconds = window_seconds

    @property
    def window_seconds(self) -> float:
        """How much of the past is kept and shown."""
        return self._window_seconds

    @window_seconds.setter
    def window_seconds(self, seconds: float) -> None:
        """Show more or less of the past, dropping what falls outside."""
        self._window_seconds = max(seconds, 0.1)
        self._recording.forget_before(self._window().start_seconds)

    def collect(self) -> None:
        """Read whatever is new, without arranging any of it.

        Worth doing on its own because the two halves want different
        rhythms. The recordings are rings and must be emptied as fast
        as the firmware fills them or a stretch of the run is lost
        for good; the picture of five seconds that comes out of them
        is read by a person, and nobody reads one twelve times a
        second.
        """
        self._recording.take_everything()
        self._recording.forget_before(self._window().start_seconds)

    def collect_given(self, samples: TraceView, exchanges: BusTraceView) -> None:
        """The same, with the two shared recordings handed in.

        A client that polls has read them already -- the scope plots
        the one and the bus table lists the other -- and decoding
        tens of thousands of records a second time costs more than
        everything else this page does put together.
        """
        self._recording.take_samples(samples)
        self._recording.take_exchanges(exchanges)
        self._recording.take_its_own()
        self._recording.forget_before(self._window().start_seconds)

    def arrange(self) -> TimelineView:
        """Hand back the window as it stands, reading nothing new."""
        channels = tuple(build_channel_view(one) for one in self._session.read_analog_channels())
        buses = tuple(build_bus_view(one) for one in self._session.read_buses())
        pins = self._session.read_gpio_pins()
        return self._view(channels, buses, pins)

    def execute(self) -> TimelineView:
        """Read what is new and hand back the whole window."""
        self.collect()
        return self.arrange()

    def clear(self) -> None:
        """Forget everything read so far and start the window again."""
        self._recording.clear()

    def _window(self) -> TimeWindow:
        """The stretch currently shown, which ends at the newest thing."""
        latest = self._recording.latest_seconds
        start = max(0.0, latest - self._window_seconds)
        return TimeWindow(start, max(latest, start + self._window_seconds))

    def _view(
        self,
        channels: tuple[ChannelView, ...],
        buses: tuple[BusView, ...],
        pins: tuple[GpioPinState, ...],
    ) -> TimelineView:
        """What the page draws."""
        window = self._window()
        lanes = (*self._pin_lanes(pins, window), *self._bus_lanes(buses), *self._call_lanes())
        # Not narrowed to the window again: the recording was told to
        # forget everything before it opened, and nothing can have
        # happened after it closed -- it closes at the newest thing
        # there is. Filtering the window twice costs the whole window
        # a second time on every reading, which on a busy bus is tens
        # of thousands of moments to walk for nothing.
        timeline = Timeline(lanes)
        recorded = timeline.recorded
        return TimelineView(
            window=build_window_view(window),
            recorded=build_window_view(recorded) if recorded is not None else None,
            curves=self._curves(channels),
            lanes=tuple(self._lane_view(one, window) for one in timeline.lanes),
        )

    def _lane_view(self, lane: TimelineLane, window: TimeWindow) -> LaneView:
        """One row, told whether everything on it was seen."""
        complete = lane.kind is not LaneKind.CALL or self._recording.calls_are_complete
        return build_lane_view(lane, window, complete)

    def _pin_lanes(
        self, pins: tuple[GpioPinState, ...], window: TimeWindow
    ) -> tuple[TimelineLane, ...]:
        """One row per pin, as the stretches it spent at a level."""
        return tuple(
            pin_lane(
                f"pin:{one.identifier.value}",
                one.identifier.label or f"pin {one.identifier.value}",
                runs_of(self._recording.pins[one.identifier.value], window.end_seconds),
            )
            for one in pins
            if one.identifier.value in self._recording.pins
        )

    def _bus_lanes(self, buses: tuple[BusView, ...]) -> tuple[TimelineLane, ...]:
        """One row per bus, named the way the firmware named it."""
        return tuple(
            bus_lane(
                f"bus:{one.bus_id}",
                one.name,
                self._recording.exchanges[one.bus_id],
                self._recording.exchange_moments[one.bus_id],
            )
            for one in buses
        )

    def _call_lanes(self) -> tuple[TimelineLane, ...]:
        """One row per peripheral the firmware called into."""
        return tuple(
            call_lane(f"call:{name}", f"{name} calls", calls, self._recording.call_moments[name])
            for name, calls in sorted(self._recording.calls.items())
        )

    def _curves(self, channels: tuple[ChannelView, ...]) -> tuple[CurveView, ...]:
        """One row per channel that published anything."""
        return tuple(
            self._curve(one) for one in channels if one.channel_id in self._recording.curves
        )

    def _curve(self, channel: ChannelView) -> CurveView:
        """One measured value, reduced to what is worth handing over.

        The range is read off the reduced points rather than off all
        of them, and loses nothing by it: each column keeps the
        lowest and the highest value that fell in it, so the highest
        of the whole curve is the highest of some column and is
        still there. One pass over a window of a hundred thousand
        samples rather than two.
        """
        window = self._window()
        points = self._recording.curves[channel.channel_id]
        reduced = decimate(points, window.start_seconds, window.duration_seconds, CURVE_COLUMNS)
        covered = value_range(reduced) or (0.0, 0.0)
        return CurveView(
            key=f"channel:{channel.channel_id}",
            label=f"{channel.name} [{channel.unit}]" if channel.unit else channel.name,
            channel_id=channel.channel_id,
            points=tuple(reduced),
            lowest=covered[0],
            highest=covered[1],
        )
