"""Translation between protocol messages and the domain model."""

from __future__ import annotations

from typing import cast

from looper.domain.model.firmware import (
    BitRange,
    FirmwareVariable,
    VariableEncoding,
    VariablePath,
    VariableWatch,
)
from looper.domain.model.simulation import (
    ActivePolarity,
    AdapterCall,
    AnalogChannel,
    AnalogSample,
    ChannelDirection,
    GpioPinState,
    PinChange,
    PinDirection,
    PinIdentifier,
    SignalDefinition,
    SignalLevel,
    SimulationTime,
    TimeMode,
    Waveform,
)
from looper.infrastructure.ipc.generated import looper_control_pb2 as protocol

DIRECTIONS: dict[int, PinDirection] = {
    protocol.PIN_DIRECTION_INPUT: PinDirection.INPUT,
    protocol.PIN_DIRECTION_OUTPUT: PinDirection.OUTPUT,
}
LEVELS: dict[int, SignalLevel] = {
    protocol.SIGNAL_LEVEL_LOW: SignalLevel.LOW,
    protocol.SIGNAL_LEVEL_HIGH: SignalLevel.HIGH,
}
POLARITIES: dict[int, ActivePolarity] = {
    protocol.ACTIVE_POLARITY_HIGH: ActivePolarity.ACTIVE_HIGH,
    protocol.ACTIVE_POLARITY_LOW: ActivePolarity.ACTIVE_LOW,
}
TIME_MODES: dict[int, TimeMode] = {
    protocol.TIME_MODE_VIRTUAL: TimeMode.VIRTUAL,
    protocol.TIME_MODE_REAL: TimeMode.REAL_TIME,
}
CHANNEL_DIRECTIONS: dict[int, ChannelDirection] = {
    protocol.CHANNEL_DIRECTION_INPUT: ChannelDirection.INPUT,
    protocol.CHANNEL_DIRECTION_OUTPUT: ChannelDirection.OUTPUT,
}
WAVEFORMS: dict[int, Waveform] = {
    protocol.WAVEFORM_CONSTANT: Waveform.CONSTANT,
    protocol.WAVEFORM_SINE: Waveform.SINE,
    protocol.WAVEFORM_SQUARE: Waveform.SQUARE,
    protocol.WAVEFORM_TRIANGLE: Waveform.TRIANGLE,
    protocol.WAVEFORM_SAWTOOTH: Waveform.SAWTOOTH,
}
WAVEFORMS_TO_PROTOCOL: dict[Waveform, int] = {
    waveform: value for value, waveform in WAVEFORMS.items()
}
LEVELS_TO_PROTOCOL: dict[SignalLevel, int] = {level: value for value, level in LEVELS.items()}
ENCODINGS: dict[int, VariableEncoding] = {
    protocol.VARIABLE_ENCODING_SIGNED: VariableEncoding.SIGNED_INTEGER,
    protocol.VARIABLE_ENCODING_UNSIGNED: VariableEncoding.UNSIGNED_INTEGER,
    protocol.VARIABLE_ENCODING_FLOAT: VariableEncoding.FLOATING_POINT,
    protocol.VARIABLE_ENCODING_BOOLEAN: VariableEncoding.BOOLEAN,
}
ENCODINGS_TO_PROTOCOL: dict[VariableEncoding, int] = {
    encoding: value for value, encoding in ENCODINGS.items()
}


def to_pin_state(pin: protocol.Pin) -> GpioPinState:
    """Translate one protocol pin into its domain representation.

    An unset enumeration falls back to the safe reading. A pin of unknown
    direction becomes an output, so a client never offers to drive something
    the firmware itself controls.
    """
    identifier = PinIdentifier(value=pin.id, label=pin.label or None)
    return GpioPinState(
        identifier=identifier,
        direction=DIRECTIONS.get(pin.direction, PinDirection.OUTPUT),
        level=LEVELS.get(pin.level, SignalLevel.LOW),
        polarity=POLARITIES.get(pin.polarity, ActivePolarity.ACTIVE_HIGH),
    )


def to_simulation_time(microseconds: int) -> SimulationTime:
    """Translate an elapsed microsecond count into its domain representation."""
    return SimulationTime(microseconds=microseconds)


def to_time_mode(value: int) -> TimeMode:
    """Translate a protocol time mode into its domain representation."""
    return TIME_MODES.get(value, TimeMode.VIRTUAL)


def from_signal_level(level: SignalLevel) -> int:
    """Translate a domain signal level into its protocol value."""
    return LEVELS_TO_PROTOCOL[level]


def to_signal(signal: protocol.Signal) -> SignalDefinition:
    """Translate a protocol signal into its domain representation."""
    return SignalDefinition(
        waveform=WAVEFORMS.get(signal.waveform, Waveform.CONSTANT),
        amplitude=abs(signal.amplitude),
        offset=signal.offset,
        frequency_hz=max(signal.frequency_hz, 0.0),
        phase_degrees=signal.phase_degrees,
    )


def from_signal(signal: SignalDefinition) -> protocol.Signal:
    """Translate a domain signal into the protocol message."""
    return protocol.Signal(
        waveform=cast(protocol.Waveform, WAVEFORMS_TO_PROTOCOL[signal.waveform]),
        amplitude=signal.amplitude,
        offset=signal.offset,
        frequency_hz=signal.frequency_hz,
        phase_degrees=signal.phase_degrees,
    )


def to_analog_channel(channel: protocol.Channel) -> AnalogChannel:
    """Translate one protocol channel into its domain representation.

    An unset direction is read as an output, so a client never offers to drive
    something the firmware itself produces.
    """
    return AnalogChannel(
        identifier=channel.id,
        label=channel.label,
        unit=channel.unit,
        direction=CHANNEL_DIRECTIONS.get(channel.direction, ChannelDirection.OUTPUT),
        value=channel.value,
        has_value=channel.has_value,
        signal=to_signal(channel.signal),
    )


def to_analog_sample(sample: protocol.Sample) -> AnalogSample:
    """Translate one recorded sample into its domain representation."""
    return AnalogSample(
        channel=sample.channel,
        microseconds=sample.microseconds,
        value=sample.value,
        sequence=sample.sequence,
    )


def to_pin_change(change: protocol.PinChange) -> PinChange:
    """Translate one recorded level change into its domain representation."""
    return PinChange(
        pin=change.pin,
        level=LEVELS.get(change.level, SignalLevel.LOW),
        microseconds=change.microseconds,
        sequence=change.sequence,
    )


def to_adapter_call(entry: protocol.JournalEntry) -> AdapterCall:
    """Translate one recorded adapter call into its domain representation."""
    return AdapterCall(
        function=entry.function,
        microseconds=entry.microseconds,
        sequence=entry.sequence,
    )


def from_variable_encoding(encoding: VariableEncoding) -> int:
    """Translate a domain encoding into its protocol value."""
    return ENCODINGS_TO_PROTOCOL[encoding]


def to_variable_watch(watch: protocol.Watch) -> VariableWatch:
    """Translate one watch into its domain representation.

    The simulation reports the variable back as it recorded it rather than
    the client remembering what it asked for, so what comes out describes
    what is actually being read.
    """
    variable = FirmwareVariable(
        path=VariablePath(watch.path),
        link_time_address=watch.address,
        encoding=ENCODINGS.get(watch.encoding, VariableEncoding.UNSIGNED_INTEGER),
        byte_width=watch.byte_width,
        is_constant=not watch.writable,
        bits=BitRange(watch.bit_offset, watch.bit_width) if watch.bit_width else None,
    )
    return VariableWatch(
        channel=watch.channel,
        variable=variable,
        runtime_address=watch.address,
        value=watch.value,
    )
