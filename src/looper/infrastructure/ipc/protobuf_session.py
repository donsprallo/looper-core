"""Simulation session backed by the protobuf control protocol."""

from __future__ import annotations

import socket
from pathlib import Path
from types import TracebackType

from looper.domain.model.firmware import FirmwareVariable, VariableWatch
from looper.domain.model.memory import HeapReading
from looper.domain.model.profile import PathReading, ProfileReading
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
from looper.infrastructure.ipc import bus_translation, translation
from looper.infrastructure.ipc import measurement_translation as measurements
from looper.infrastructure.ipc.errors import (
    ProtocolMismatchError,
    SimulationUnreachableError,
)
from looper.infrastructure.ipc.generated import looper_control_pb2 as protocol
from looper.infrastructure.ipc.request_exchange import RequestExchange

#: The first node worth asking for. Zero is the root, which is not
#: a function and which the simulation never sends.
FIRST_PATH = 1

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 45771
DEFAULT_TIMEOUT_SECONDS = 2.0

#: Version of the control protocol this client speaks. It has to match
#: LOOPER_PROTOCOL_VERSION in the runtime's looper_protocol.h, which
#: tests/infrastructure/ipc/test_protocol_version.py checks.
PROTOCOL_VERSION = 1

#: What a runtime built before the protocol carried a version answers,
#: because proto3 cannot tell an unset number from a zero.
UNVERSIONED = 0

UNVERSIONED_MESSAGE = (
    "The simulation was built before the control protocol carried a version, "
    "so this client cannot tell whether it can read it. Rebuild it with "
    "looper-cli build."
)


class ProtobufSimulationSession(SimulationSession):
    """Talks to a running simulation over a TCP control channel.

    One request is answered by exactly one response, so a session must not be
    shared between threads. A graphical client keeps it on its worker thread
    and never touches it from the interface thread.
    """

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._connection = self._connect(host, port, timeout)
        self._exchange = RequestExchange(self._connection).send
        greeting = self._hello()
        self._check_protocol(greeting.protocol_version)
        self._time_mode = translation.to_time_mode(greeting.time_mode)
        self._firmware_name = greeting.firmware
        self._executable = Path(greeting.image.executable) if greeting.image.executable else None
        self._runtime_base = greeting.image.runtime_base

    @staticmethod
    def _connect(host: str, port: int, timeout: float) -> socket.socket:
        """Open the control channel.

        Raises:
            SimulationUnreachableError: If no simulation is listening.
        """
        try:
            return socket.create_connection((host, port), timeout=timeout)
        except OSError as error:
            raise SimulationUnreachableError(f"No simulation at {host}:{port}: {error}") from error

    @property
    def is_connected(self) -> bool:
        """Whether the session still holds an open channel."""
        return self._connection.fileno() != -1

    @property
    def firmware_name(self) -> str:
        """Name the simulation reported when the session was opened."""
        return self._firmware_name

    @property
    def time_mode(self) -> TimeMode:
        """The time source the connected firmware was started with."""
        return self._time_mode

    def read_time(self) -> SimulationTime:
        """Read the current elapsed firmware time."""
        response = self._exchange(protocol.COMMAND_READ_TIME)
        return translation.to_simulation_time(response.microseconds)

    def read_gpio_pins(self) -> tuple[GpioPinState, ...]:
        """Read the state of every pin the firmware has registered."""
        response = self._exchange(protocol.COMMAND_LIST_PINS)
        return tuple(translation.to_pin_state(pin) for pin in response.pins)

    def drive_input_pin(self, identifier: PinIdentifier, level: SignalLevel) -> None:
        """Apply an electrical level to a pin the firmware reads.

        Raises:
            SimulationRejectedError: If the pin is unknown or is an output.
        """
        self._exchange(
            protocol.COMMAND_DRIVE_PIN,
            pin=identifier.value,
            level=translation.from_signal_level(level),
        )

    def read_analog_channels(self) -> tuple[AnalogChannel, ...]:
        """Read every analog channel the firmware has registered."""
        response = self._exchange(protocol.COMMAND_LIST_CHANNELS)
        return tuple(translation.to_analog_channel(channel) for channel in response.channels)

    def set_signal(self, channel: int, signal: SignalDefinition) -> None:
        """Install the signal that drives an analog input.

        Raises:
            SimulationRejectedError: If the channel is unknown or is an output.
        """
        self._exchange(
            protocol.COMMAND_SET_SIGNAL, channel=channel, signal=translation.from_signal(signal)
        )

    def read_trace(self, after_sequence: int = 0) -> tuple[tuple[AnalogSample, ...], int]:
        """Read the analog samples recorded after a sequence number."""
        response = self._exchange(protocol.COMMAND_READ_TRACE, after_sequence=after_sequence)
        samples = tuple(translation.to_analog_sample(sample) for sample in response.samples)
        return samples, response.next_sequence

    def clear_trace(self) -> None:
        """Discard the recorded analog samples."""
        self._exchange(protocol.COMMAND_CLEAR_TRACE)

    def advance_time(self, microseconds: int) -> SimulationTime:
        """Advance the virtual clock.

        Raises:
            SimulationRejectedError: If the firmware runs in real time.
        """
        response = self._exchange(protocol.COMMAND_ADVANCE_TIME, microseconds=microseconds)
        return translation.to_simulation_time(response.microseconds)

    def read_pin_trace(self, after_sequence: int = 0) -> tuple[tuple[PinChange, ...], int]:
        """Read the level changes recorded after a sequence number."""
        response = self._exchange(protocol.COMMAND_READ_PIN_TRACE, after_sequence=after_sequence)
        changes = tuple(translation.to_pin_change(one) for one in response.pin_changes)
        return changes, response.next_sequence

    def clear_pin_trace(self) -> None:
        """Discard the recorded level changes."""
        self._exchange(protocol.COMMAND_CLEAR_PIN_TRACE)

    def read_journal(self) -> tuple[AdapterCall, ...]:
        """Read the adapter calls the firmware recorded."""
        response = self._exchange(protocol.COMMAND_READ_JOURNAL)
        return tuple(translation.to_adapter_call(entry) for entry in response.journal)

    def clear_journal(self) -> None:
        """Discard the recorded adapter calls."""
        self._exchange(protocol.COMMAND_CLEAR_JOURNAL)

    @property
    def executable(self) -> Path | None:
        """Path of the running executable, which carries the debug information."""
        return self._executable

    def read_runtime_base(self) -> int:
        """Read the address the running process was loaded at.

        Reported once in the greeting: a process does not move while it runs.
        """
        return self._runtime_base

    def read_variable_watches(self) -> tuple[VariableWatch, ...]:
        """Read every variable the simulation is currently sampling."""
        response = self._exchange(protocol.COMMAND_LIST_WATCHES)
        return tuple(translation.to_variable_watch(watch) for watch in response.watches)

    def watch_variable(self, variable: FirmwareVariable, runtime_address: int) -> VariableWatch:
        """Start sampling a firmware variable into the trace.

        Raises:
            SimulationRejectedError: If the address is not readable or no
                watch is free.
        """
        response = self._exchange(
            protocol.COMMAND_WATCH_VARIABLE,
            path=variable.path.text,
            address=runtime_address,
            encoding=translation.from_variable_encoding(variable.encoding),
            byte_width=variable.byte_width,
            bit_offset=variable.bits.offset if variable.bits is not None else 0,
            bit_width=variable.bits.width if variable.bits is not None else 0,
            writable=variable.is_writable,
        )
        return translation.to_variable_watch(response.watches[0])

    def remove_variable_watch(self, channel: int) -> None:
        """Stop sampling a watched variable.

        Raises:
            SimulationRejectedError: If no watch holds that channel.
        """
        self._exchange(protocol.COMMAND_REMOVE_WATCH, channel=channel)

    def write_variable(self, channel: int, value: float) -> None:
        """Write a value into a watched firmware variable.

        Raises:
            SimulationRejectedError: If the watch is unknown, the variable is
                constant, or the value is outside the range it can hold.
        """
        self._exchange(protocol.COMMAND_WRITE_VARIABLE, channel=channel, value=value)

    def read_buses(self) -> tuple[SimulatedBus, ...]:
        """Read every bus the simulation models."""
        response = self._exchange(protocol.COMMAND_LIST_BUSES)
        return tuple(bus_translation.to_bus(bus) for bus in response.buses)

    def read_components(self) -> tuple[ComponentDescription, ...]:
        """Read every component attached to those buses.

        A component says which bus it is on but not what kind of bus that
        is, so the bus listing is read first and the kinds taken from there.
        """
        kinds = {bus.identifier: bus.kind for bus in self.read_buses()}
        response = self._exchange(protocol.COMMAND_LIST_COMPONENTS)
        return tuple(
            bus_translation.to_component(component, kinds[component.bus])
            for component in response.components
            if component.bus in kinds
        )

    def read_bus_trace(self, after_sequence: int = 0) -> tuple[tuple[BusTraceEntry, ...], int]:
        """Read the exchanges recorded after a sequence number."""
        response = self._exchange(protocol.COMMAND_READ_BUS_TRACE, after_sequence=after_sequence)
        records = tuple(bus_translation.to_bus_trace_entry(record) for record in response.exchanges)
        return records, response.next_bus_sequence

    def clear_bus_trace(self) -> None:
        """Discard the recorded exchanges."""
        self._exchange(protocol.COMMAND_CLEAR_BUS_TRACE)

    def attach_component(self, bus: int, address: BusAddress, label: str) -> None:
        """Take the part of a peer on a bus, so that it is listed.

        Raises:
            SimulationRejectedError: If the bus will not take one.
        """
        self._exchange(
            protocol.COMMAND_ATTACH_COMPONENT,
            bus=bus,
            bus_address=bus_translation.from_bus_address(address),
            label=label,
        )

    def detach_component(self, bus: int, address: BusAddress) -> None:
        """Stop taking a peer's part.

        Raises:
            SimulationRejectedError: If nothing is attached there.
        """
        self._exchange(
            protocol.COMMAND_DETACH_COMPONENT,
            bus=bus,
            bus_address=bus_translation.from_bus_address(address),
        )

    def send_bus_message(self, bus: int, message: BusMessage) -> None:
        """Put one message on a bus for the firmware to receive.

        Raises:
            SimulationRejectedError: If the bus is unknown or is full.
        """
        address, payload = bus_translation.from_bus_message(message)
        self._exchange(
            protocol.COMMAND_SEND_BUS_MESSAGE, bus=bus, bus_address=address, payload=payload
        )

    def read_call_timings(self) -> tuple[CallTiming, ...]:
        """Read what was measured at the adapter boundary."""
        response = self._exchange(protocol.COMMAND_READ_TIMINGS)
        return tuple(measurements.to_call_timing(timing) for timing in response.timings)

    def clear_call_timings(self) -> None:
        """Forget the measurements and start again."""
        self._exchange(protocol.COMMAND_CLEAR_TIMINGS)

    def read_profile(self, after_position: int = 0) -> ProfileReading:
        """Read one page of where the whole simulation spent its time."""
        response = self._exchange(protocol.COMMAND_READ_PROFILE, after_sequence=after_position)
        return measurements.to_profile_page(response)

    def read_profile_paths(self, after_position: int = 0) -> PathReading:
        """Read one page of the tree of call paths."""
        position = max(after_position, FIRST_PATH)
        response = self._exchange(protocol.COMMAND_READ_PROFILE_PATHS, after_sequence=position)
        return measurements.to_path_reading(response, position)

    def watch_profile_paths(self, wanted: bool) -> None:
        """Begin, or stop, following which way the calls go."""
        self._exchange(protocol.COMMAND_WATCH_PROFILE_PATHS, watching=wanted)

    def clear_profile(self) -> None:
        """Forget the profile and begin a new window."""
        self._exchange(protocol.COMMAND_CLEAR_PROFILE)

    def read_heap(self) -> HeapReading:
        """Read what the firmware has asked the allocator for."""
        return measurements.to_heap_reading(self._exchange(protocol.COMMAND_READ_HEAP))

    def clear_heap(self) -> None:
        """Forget the counts and begin the peak again."""
        self._exchange(protocol.COMMAND_CLEAR_HEAP)

    def close(self) -> None:
        """Release the channel. Closing an already closed session is allowed."""
        self._connection.close()

    def __enter__(self) -> ProtobufSimulationSession:
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    @staticmethod
    def _check_protocol(reported: int) -> None:
        """Refuse a simulation whose wire format this client cannot read.

        Args:
            reported: The version the simulation answered COMMAND_HELLO with.

        Raises:
            ProtocolMismatchError: If it is not the one this client speaks.
        """
        if reported == PROTOCOL_VERSION:
            return
        if reported == UNVERSIONED:
            raise ProtocolMismatchError(UNVERSIONED_MESSAGE)
        raise ProtocolMismatchError(
            f"The simulation speaks control protocol {reported} and this "
            f"client speaks {PROTOCOL_VERSION}. Rebuild one of them so that "
            f"they agree."
        )

    def _hello(self) -> protocol.Response:
        """Identify the simulation and learn its time mode."""
        return self._exchange(protocol.COMMAND_HELLO)
