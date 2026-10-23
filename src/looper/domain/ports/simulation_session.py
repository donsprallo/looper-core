"""The outbound interface to one running simulated firmware instance.

What this promises includes how it says no. A simulation refuses
things as a matter of course -- an output pin is not a client's to
drive, a virtual clock is not steerable in real time -- and a
client has to tell that from a session that has broken, because it
shows the one beside the form that asked for it and ends on the
other. So the refusal has a type of its own, named here rather than
by whichever adapter is behind the port.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from looper.domain.model.firmware.firmware_variable import FirmwareVariable
from looper.domain.model.firmware.variable_watch import VariableWatch
from looper.domain.model.memory.heap_reading import HeapReading
from looper.domain.model.profile.measured_function import ProfileReading
from looper.domain.model.profile.measured_path import PathReading
from looper.domain.model.simulation.adapter_call import AdapterCall
from looper.domain.model.simulation.analog_channel import (
    AnalogChannel,
    AnalogSample,
    SignalDefinition,
)
from looper.domain.model.simulation.bus import (
    BusAddress,
    ComponentDescription,
    SimulatedBus,
)
from looper.domain.model.simulation.bus_traffic import BusMessage, BusTraceEntry
from looper.domain.model.simulation.call_timing import CallTiming
from looper.domain.model.simulation.gpio_pin import GpioPinState, SignalLevel
from looper.domain.model.simulation.pin_change import PinChange
from looper.domain.model.simulation.pin_identifier import PinIdentifier
from looper.domain.model.simulation.simulation_time import SimulationTime
from looper.domain.model.simulation.time_mode import TimeMode


class SimulationSession(ABC):
    """A connection to one running simulated firmware instance."""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Whether the session can currently reach the firmware process."""

    @property
    @abstractmethod
    def time_mode(self) -> TimeMode:
        """The time source the connected firmware was started with."""

    @abstractmethod
    def read_time(self) -> SimulationTime:
        """Read the firmware's current elapsed time."""

    @abstractmethod
    def read_gpio_pins(self) -> tuple[GpioPinState, ...]:
        """Read the state of every pin the firmware has registered."""

    @abstractmethod
    def drive_input_pin(self, identifier: PinIdentifier, level: SignalLevel) -> None:
        """Apply an electrical level to a pin the firmware reads.

        Args:
            identifier: Pin to drive.
            level: Level to apply.

        Raises:
            SimulationRejectedError: If the pin is an output and cannot be driven.
        """

    @abstractmethod
    def read_analog_channels(self) -> tuple[AnalogChannel, ...]:
        """Read every analog channel the firmware has registered."""

    @abstractmethod
    def set_signal(self, channel: int, signal: SignalDefinition) -> None:
        """Install the signal that drives an analog input.

        Args:
            channel: Channel to drive.
            signal: Signal the simulation evaluates on every firmware read.

        Raises:
            SimulationRejectedError: If the channel is unknown or the firmware drives it.
        """

    @abstractmethod
    def read_trace(self, after_sequence: int = 0) -> tuple[tuple[AnalogSample, ...], int]:
        """Read the analog samples recorded after a sequence number.

        Args:
            after_sequence: Sequence number the caller has already seen.

        Returns:
            The samples, oldest first, and the sequence number to ask for next.
        """

    @property
    @abstractmethod
    def executable(self) -> Path | None:
        """Path of the running executable, which carries the debug information.

        ``None`` when the simulation could not locate its own file, which is
        what a platform the runtime has no answer for reports.
        """

    @abstractmethod
    def read_runtime_base(self) -> int:
        """Read the address the running process was loaded at.

        Half of what translating a link time address needs; the other half is
        the base the executable was linked against, which only the file can
        say. See :class:`DebugInformationReader`.
        """

    @abstractmethod
    def read_variable_watches(self) -> tuple[VariableWatch, ...]:
        """Read every variable the simulation is currently sampling."""

    @abstractmethod
    def watch_variable(self, variable: FirmwareVariable, runtime_address: int) -> VariableWatch:
        """Start sampling a firmware variable into the trace.

        Args:
            variable: Variable to read, as the debug information describes it.
            runtime_address: Its address in the running process.

        Returns:
            The watch, carrying the trace channel the simulation allocated.

        Raises:
            SimulationRejectedError: If the address is not readable or no channel is free.
        """

    @abstractmethod
    def remove_variable_watch(self, channel: int) -> None:
        """Stop sampling a watched variable.

        Args:
            channel: Trace channel of the watch to remove.

        Raises:
            SimulationRejectedError: If no watch holds that channel.
        """

    @abstractmethod
    def write_variable(self, channel: int, value: float) -> None:
        """Write a value into a watched firmware variable.

        Args:
            channel: Trace channel of the watch to write through.
            value: Value to store, converted to the variable's encoding.

        Raises:
            SimulationRejectedError: If the watch is unknown, the variable is constant, or
                the value is outside the range the variable can hold.
        """

    @abstractmethod
    def clear_trace(self) -> None:
        """Discard the recorded analog samples."""

    @abstractmethod
    def advance_time(self, microseconds: int) -> SimulationTime:
        """Advance the virtual clock, and report where it now stands.

        Raises:
            SimulationRejectedError: If the firmware runs in real time.
        """

    @abstractmethod
    def read_buses(self) -> tuple[SimulatedBus, ...]:
        """Read every bus the simulation models."""

    @abstractmethod
    def read_components(self) -> tuple[ComponentDescription, ...]:
        """Read every component attached to those buses."""

    @abstractmethod
    def read_bus_trace(self, after_sequence: int = 0) -> tuple[tuple[BusTraceEntry, ...], int]:
        """Read the exchanges recorded after a sequence number.

        Args:
            after_sequence: Sequence number the caller has already seen.

        Returns:
            The records, and the sequence number the next one will carry.
        """

    @abstractmethod
    def clear_bus_trace(self) -> None:
        """Discard the recorded exchanges."""

    @abstractmethod
    def read_pin_trace(self, after_sequence: int = 0) -> tuple[tuple[PinChange, ...], int]:
        """Read the level changes recorded after a sequence number.

        The pins themselves say what every one of them is now. This
        says when it became that, which is the question a bus raises
        and a snapshot cannot answer.

        Args:
            after_sequence: Sequence number the caller has already seen.

        Returns:
            The changes, and the sequence number the next one will
            carry.
        """

    @abstractmethod
    def clear_pin_trace(self) -> None:
        """Discard the recorded level changes."""

    @abstractmethod
    def read_journal(self) -> tuple[AdapterCall, ...]:
        """Read the adapter calls the firmware recorded.

        The timing report says how often a function was called and
        what one call cost. This says when each call happened, which
        is what puts the calls on a ruler beside everything else.

        Returns:
            The calls still held, oldest first. The journal is a ring
            and a response carries at most a page of it, so a caller
            that wants them all reads often.
        """

    @abstractmethod
    def clear_journal(self) -> None:
        """Discard the recorded adapter calls."""

    @abstractmethod
    def attach_component(self, bus: int, address: BusAddress, label: str) -> None:
        """Take the part of a peer on a bus, so that it is listed.

        Refused on SPI and I2C. There the firmware is the master and
        expects an answer inside the call it made, which nothing on the
        other end of a channel can give in time.

        Args:
            bus: Bus to attach to.
            address: Where on that bus the peer answers.
            label: What to call it in the listing.

        Raises:
            SimulationRejectedError: If the bus is unknown, the firmware masters it, or
                something is already at that address.
        """

    @abstractmethod
    def detach_component(self, bus: int, address: BusAddress) -> None:
        """Stop taking a peer's part.

        Raises:
            SimulationRejectedError: If nothing is attached there.
        """

    @abstractmethod
    def send_bus_message(self, bus: int, message: BusMessage) -> None:
        """Put one message on a bus for the firmware to receive.

        Whether the firmware is given it depends on the controller being
        simulated, whose filters the simulation applies; the recording says
        which way it went.

        Args:
            bus: Bus to put the message on.
            message: Message to send.

        Raises:
            SimulationRejectedError: If the bus is unknown or is holding all it can.
        """

    @abstractmethod
    def read_call_timings(self) -> tuple[CallTiming, ...]:
        """Read what was measured at the adapter boundary.

        How often each call was made, how long it took in host time, and
        how often anything answered it.
        """

    @abstractmethod
    def clear_call_timings(self) -> None:
        """Forget the measurements and start again."""

    @abstractmethod
    def read_profile(self, after_position: int = 0) -> ProfileReading:
        """Read one page of where the whole simulation spent its time.

        Every instrumented function that ran, which is more than one
        reply carries, so this is read until the position it hands back
        stops moving.

        Args:
            after_position: Position the caller has already read to.
        """

    @abstractmethod
    def read_profile_paths(self, after_position: int = 0) -> PathReading:
        """Read one page of the tree of call paths.

        What a flame graph is drawn from. The ranking says what a
        function cost altogether; this says what it cost reached one
        particular way, which is nearly always the question that
        follows.

        Args:
            after_position: Position the caller has already read to.
        """

    @abstractmethod
    def watch_profile_paths(self, wanted: bool) -> None:
        """Begin, or stop, following which way the calls go.

        Following them costs more than the ranking does, so it is
        armed by whoever wants the picture. Arming begins a window
        of its own.
        """

    @abstractmethod
    def clear_profile(self) -> None:
        """Forget the profile and begin a new window."""

    @abstractmethod
    def read_heap(self) -> HeapReading:
        """Read what the firmware has asked the allocator for."""

    @abstractmethod
    def clear_heap(self) -> None:
        """Forget the counts and begin the peak again.

        What is still out is not forgotten: it is still out.
        """

    @abstractmethod
    def close(self) -> None:
        """Release the channel. Closing an already closed session is allowed."""
