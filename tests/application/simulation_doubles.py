"""A simulation session that records what was asked of it.

The use cases under test talk to a simulation through one port. Recording
what reaches that port is how a test says what a use case did, without a
process, a socket, or a build anywhere in sight.

What it answers with is a script of one run rather than a live recording,
so asking it to clear a recording is noted in ``cleared`` and changes
nothing: a test that scripted a window wants to see that window, and a
test about clearing wants to see that the use case asked.
"""

from __future__ import annotations

from pathlib import Path

from looper.domain.model.firmware import FirmwareVariable, VariableWatch
from looper.domain.model.memory import HeapReading
from looper.domain.model.profile import (
    MeasuredFunction,
    MeasuredPath,
    PathReading,
    ProfileReading,
)
from looper.domain.model.simulation import (
    AdapterCall,
    AnalogChannel,
    AnalogSample,
    BusAddress,
    BusMessage,
    BusTraceEntry,
    CallTiming,
    ComponentDescription,
    GpioPinState,
    PinChange,
    PinIdentifier,
    SignalDefinition,
    SignalLevel,
    SimulatedBus,
    SimulationTime,
    TimeMode,
)
from looper.domain.ports import SimulationSession

WATCH_CHANNEL_BASE = 0x8000_0000


class RecordingSession(SimulationSession):
    """A session that answers from fixed state and remembers every request."""

    def __init__(
        self,
        executable: Path | None = None,
        runtime_base: int = 1,
        watches: tuple[VariableWatch, ...] = (),
    ) -> None:
        self._executable = executable
        self._runtime_base = runtime_base
        self.watches = watches
        self.watched: list[tuple[FirmwareVariable, int]] = []
        self.removed: list[int] = []
        self.written: list[tuple[int, float]] = []
        self.buses: tuple[SimulatedBus, ...] = ()
        self.components: tuple[ComponentDescription, ...] = ()
        self.exchanges: tuple[BusTraceEntry, ...] = ()
        self.calls: tuple[AdapterCall, ...] = ()
        self.pin_changes: tuple[PinChange, ...] = ()
        self.pins: tuple[GpioPinState, ...] = ()
        self.paths: tuple[MeasuredPath, ...] = ()
        self.watching_paths = False
        self.sent: list[tuple[int, BusMessage]] = []
        self.attached: list[tuple[int, BusAddress, str]] = []
        self.detached: list[tuple[int, BusAddress]] = []
        self.timings: tuple[CallTiming, ...] = ()
        self.measurements: tuple[MeasuredFunction, ...] = ()
        self.channels: tuple[AnalogChannel, ...] = ()
        self.heap = HeapReading()
        self.deepest_stack_bytes = 0
        self.deepest_depth = 0
        self.stack_path: tuple[int, ...] = ()
        self.samples: tuple[AnalogSample, ...] = ()
        self.advanced = 0
        self.cleared: list[str] = []
        self.closed = False

    @property
    def is_connected(self) -> bool:
        return not self.closed

    @property
    def time_mode(self) -> TimeMode:
        return TimeMode.VIRTUAL

    @property
    def executable(self) -> Path | None:
        return self._executable

    def read_time(self) -> SimulationTime:
        return SimulationTime(microseconds=self.advanced)

    def read_gpio_pins(self) -> tuple[GpioPinState, ...]:
        return self.pins

    def drive_input_pin(self, identifier: PinIdentifier, level: SignalLevel) -> None:
        raise NotImplementedError

    def read_analog_channels(self) -> tuple[AnalogChannel, ...]:
        return self.channels

    def set_signal(self, channel: int, signal: SignalDefinition) -> None:
        raise NotImplementedError

    def read_trace(self, after_sequence: int = 0) -> tuple[tuple[AnalogSample, ...], int]:
        kept = tuple(one for one in self.samples if one.sequence >= after_sequence)
        return kept, len(self.samples)

    def clear_trace(self) -> None:
        self.cleared.append("trace")

    def advance_time(self, microseconds: int) -> SimulationTime:
        self.advanced += microseconds
        return SimulationTime(microseconds=self.advanced)

    def read_runtime_base(self) -> int:
        return self._runtime_base

    def read_variable_watches(self) -> tuple[VariableWatch, ...]:
        return self.watches

    def watch_variable(self, variable: FirmwareVariable, runtime_address: int) -> VariableWatch:
        self.watched.append((variable, runtime_address))
        watch = VariableWatch(
            channel=WATCH_CHANNEL_BASE + len(self.watched) - 1,
            variable=variable,
            runtime_address=runtime_address,
        )
        self.watches = (*self.watches, watch)
        return watch

    def remove_variable_watch(self, channel: int) -> None:
        self.removed.append(channel)

    def write_variable(self, channel: int, value: float) -> None:
        self.written.append((channel, value))

    def read_buses(self) -> tuple[SimulatedBus, ...]:
        return self.buses

    def read_components(self) -> tuple[ComponentDescription, ...]:
        return self.components

    def read_bus_trace(self, after_sequence: int = 0) -> tuple[tuple[BusTraceEntry, ...], int]:
        records = tuple(entry for entry in self.exchanges if entry.sequence >= after_sequence)
        return records, len(self.exchanges)

    def clear_bus_trace(self) -> None:
        self.cleared.append("bus trace")

    def read_pin_trace(self, after_sequence: int = 0) -> tuple[tuple[PinChange, ...], int]:
        changes = tuple(one for one in self.pin_changes if one.sequence >= after_sequence)
        return changes, len(self.pin_changes)

    def clear_pin_trace(self) -> None:
        self.cleared.append("pin trace")

    def read_journal(self) -> tuple[AdapterCall, ...]:
        return self.calls

    def clear_journal(self) -> None:
        self.cleared.append("journal")

    def attach_component(self, bus: int, address: BusAddress, label: str) -> None:
        self.attached.append((bus, address, label))

    def detach_component(self, bus: int, address: BusAddress) -> None:
        self.detached.append((bus, address))

    def send_bus_message(self, bus: int, message: BusMessage) -> None:
        self.sent.append((bus, message))

    def read_call_timings(self) -> tuple[CallTiming, ...]:
        return self.timings

    def clear_call_timings(self) -> None:
        self.cleared.append("timings")

    def read_profile(self, after_position: int = 0) -> ProfileReading:
        measurements = self.measurements[after_position:]
        return ProfileReading(
            measurements=measurements,
            next_position=after_position + len(measurements),
            is_profiling=bool(self.measurements),
            deepest_stack_bytes=self.deepest_stack_bytes,
            deepest_depth=self.deepest_depth,
            stack_path=self.stack_path,
        )

    def read_profile_paths(self, after_position: int = 0) -> PathReading:
        return PathReading(paths=self.paths, is_watched=self.watching_paths)

    def watch_profile_paths(self, wanted: bool) -> None:
        self.watching_paths = wanted

    def clear_profile(self) -> None:
        self.cleared.append("profile")

    def read_heap(self) -> HeapReading:
        return self.heap

    def clear_heap(self) -> None:
        self.cleared.append("heap")

    def close(self) -> None:
        self.closed = True
