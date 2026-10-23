from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Command(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    COMMAND_UNSPECIFIED: _ClassVar[Command]
    COMMAND_HELLO: _ClassVar[Command]
    COMMAND_READ_TIME: _ClassVar[Command]
    COMMAND_LIST_PINS: _ClassVar[Command]
    COMMAND_DRIVE_PIN: _ClassVar[Command]
    COMMAND_ADVANCE_TIME: _ClassVar[Command]
    COMMAND_READ_JOURNAL: _ClassVar[Command]
    COMMAND_CLEAR_JOURNAL: _ClassVar[Command]
    COMMAND_LIST_CHANNELS: _ClassVar[Command]
    COMMAND_SET_SIGNAL: _ClassVar[Command]
    COMMAND_READ_TRACE: _ClassVar[Command]
    COMMAND_CLEAR_TRACE: _ClassVar[Command]
    COMMAND_LIST_WATCHES: _ClassVar[Command]
    COMMAND_WATCH_VARIABLE: _ClassVar[Command]
    COMMAND_REMOVE_WATCH: _ClassVar[Command]
    COMMAND_WRITE_VARIABLE: _ClassVar[Command]
    COMMAND_LIST_BUSES: _ClassVar[Command]
    COMMAND_READ_BUS_TRACE: _ClassVar[Command]
    COMMAND_CLEAR_BUS_TRACE: _ClassVar[Command]
    COMMAND_SEND_BUS_MESSAGE: _ClassVar[Command]
    COMMAND_LIST_COMPONENTS: _ClassVar[Command]
    COMMAND_READ_TIMINGS: _ClassVar[Command]
    COMMAND_CLEAR_TIMINGS: _ClassVar[Command]
    COMMAND_READ_PROFILE: _ClassVar[Command]
    COMMAND_CLEAR_PROFILE: _ClassVar[Command]
    COMMAND_READ_HEAP: _ClassVar[Command]
    COMMAND_CLEAR_HEAP: _ClassVar[Command]
    COMMAND_READ_PIN_TRACE: _ClassVar[Command]
    COMMAND_CLEAR_PIN_TRACE: _ClassVar[Command]
    COMMAND_READ_PROFILE_PATHS: _ClassVar[Command]
    COMMAND_WATCH_PROFILE_PATHS: _ClassVar[Command]
    COMMAND_ATTACH_COMPONENT: _ClassVar[Command]
    COMMAND_DETACH_COMPONENT: _ClassVar[Command]

class VariableEncoding(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    VARIABLE_ENCODING_UNSPECIFIED: _ClassVar[VariableEncoding]
    VARIABLE_ENCODING_SIGNED: _ClassVar[VariableEncoding]
    VARIABLE_ENCODING_UNSIGNED: _ClassVar[VariableEncoding]
    VARIABLE_ENCODING_FLOAT: _ClassVar[VariableEncoding]
    VARIABLE_ENCODING_BOOLEAN: _ClassVar[VariableEncoding]

class Waveform(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    WAVEFORM_CONSTANT: _ClassVar[Waveform]
    WAVEFORM_SINE: _ClassVar[Waveform]
    WAVEFORM_SQUARE: _ClassVar[Waveform]
    WAVEFORM_TRIANGLE: _ClassVar[Waveform]
    WAVEFORM_SAWTOOTH: _ClassVar[Waveform]

class ChannelDirection(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CHANNEL_DIRECTION_UNSPECIFIED: _ClassVar[ChannelDirection]
    CHANNEL_DIRECTION_INPUT: _ClassVar[ChannelDirection]
    CHANNEL_DIRECTION_OUTPUT: _ClassVar[ChannelDirection]

class Status(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    STATUS_UNSPECIFIED: _ClassVar[Status]
    STATUS_OK: _ClassVar[Status]
    STATUS_INVALID_ARGUMENT: _ClassVar[Status]
    STATUS_UNSUPPORTED: _ClassVar[Status]

class TimeMode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TIME_MODE_UNSPECIFIED: _ClassVar[TimeMode]
    TIME_MODE_VIRTUAL: _ClassVar[TimeMode]
    TIME_MODE_REAL: _ClassVar[TimeMode]

class PinDirection(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PIN_DIRECTION_UNSPECIFIED: _ClassVar[PinDirection]
    PIN_DIRECTION_INPUT: _ClassVar[PinDirection]
    PIN_DIRECTION_OUTPUT: _ClassVar[PinDirection]

class SignalLevel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SIGNAL_LEVEL_UNSPECIFIED: _ClassVar[SignalLevel]
    SIGNAL_LEVEL_LOW: _ClassVar[SignalLevel]
    SIGNAL_LEVEL_HIGH: _ClassVar[SignalLevel]

class ActivePolarity(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ACTIVE_POLARITY_UNSPECIFIED: _ClassVar[ActivePolarity]
    ACTIVE_POLARITY_HIGH: _ClassVar[ActivePolarity]
    ACTIVE_POLARITY_LOW: _ClassVar[ActivePolarity]

class BusKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    BUS_KIND_UNSPECIFIED: _ClassVar[BusKind]
    BUS_KIND_SPI: _ClassVar[BusKind]
    BUS_KIND_I2C: _ClassVar[BusKind]
    BUS_KIND_UART: _ClassVar[BusKind]
    BUS_KIND_CAN: _ClassVar[BusKind]

class BusDirection(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    BUS_DIRECTION_UNSPECIFIED: _ClassVar[BusDirection]
    BUS_DIRECTION_OUTBOUND: _ClassVar[BusDirection]
    BUS_DIRECTION_INBOUND: _ClassVar[BusDirection]
COMMAND_UNSPECIFIED: Command
COMMAND_HELLO: Command
COMMAND_READ_TIME: Command
COMMAND_LIST_PINS: Command
COMMAND_DRIVE_PIN: Command
COMMAND_ADVANCE_TIME: Command
COMMAND_READ_JOURNAL: Command
COMMAND_CLEAR_JOURNAL: Command
COMMAND_LIST_CHANNELS: Command
COMMAND_SET_SIGNAL: Command
COMMAND_READ_TRACE: Command
COMMAND_CLEAR_TRACE: Command
COMMAND_LIST_WATCHES: Command
COMMAND_WATCH_VARIABLE: Command
COMMAND_REMOVE_WATCH: Command
COMMAND_WRITE_VARIABLE: Command
COMMAND_LIST_BUSES: Command
COMMAND_READ_BUS_TRACE: Command
COMMAND_CLEAR_BUS_TRACE: Command
COMMAND_SEND_BUS_MESSAGE: Command
COMMAND_LIST_COMPONENTS: Command
COMMAND_READ_TIMINGS: Command
COMMAND_CLEAR_TIMINGS: Command
COMMAND_READ_PROFILE: Command
COMMAND_CLEAR_PROFILE: Command
COMMAND_READ_HEAP: Command
COMMAND_CLEAR_HEAP: Command
COMMAND_READ_PIN_TRACE: Command
COMMAND_CLEAR_PIN_TRACE: Command
COMMAND_READ_PROFILE_PATHS: Command
COMMAND_WATCH_PROFILE_PATHS: Command
COMMAND_ATTACH_COMPONENT: Command
COMMAND_DETACH_COMPONENT: Command
VARIABLE_ENCODING_UNSPECIFIED: VariableEncoding
VARIABLE_ENCODING_SIGNED: VariableEncoding
VARIABLE_ENCODING_UNSIGNED: VariableEncoding
VARIABLE_ENCODING_FLOAT: VariableEncoding
VARIABLE_ENCODING_BOOLEAN: VariableEncoding
WAVEFORM_CONSTANT: Waveform
WAVEFORM_SINE: Waveform
WAVEFORM_SQUARE: Waveform
WAVEFORM_TRIANGLE: Waveform
WAVEFORM_SAWTOOTH: Waveform
CHANNEL_DIRECTION_UNSPECIFIED: ChannelDirection
CHANNEL_DIRECTION_INPUT: ChannelDirection
CHANNEL_DIRECTION_OUTPUT: ChannelDirection
STATUS_UNSPECIFIED: Status
STATUS_OK: Status
STATUS_INVALID_ARGUMENT: Status
STATUS_UNSUPPORTED: Status
TIME_MODE_UNSPECIFIED: TimeMode
TIME_MODE_VIRTUAL: TimeMode
TIME_MODE_REAL: TimeMode
PIN_DIRECTION_UNSPECIFIED: PinDirection
PIN_DIRECTION_INPUT: PinDirection
PIN_DIRECTION_OUTPUT: PinDirection
SIGNAL_LEVEL_UNSPECIFIED: SignalLevel
SIGNAL_LEVEL_LOW: SignalLevel
SIGNAL_LEVEL_HIGH: SignalLevel
ACTIVE_POLARITY_UNSPECIFIED: ActivePolarity
ACTIVE_POLARITY_HIGH: ActivePolarity
ACTIVE_POLARITY_LOW: ActivePolarity
BUS_KIND_UNSPECIFIED: BusKind
BUS_KIND_SPI: BusKind
BUS_KIND_I2C: BusKind
BUS_KIND_UART: BusKind
BUS_KIND_CAN: BusKind
BUS_DIRECTION_UNSPECIFIED: BusDirection
BUS_DIRECTION_OUTBOUND: BusDirection
BUS_DIRECTION_INBOUND: BusDirection

class Pin(_message.Message):
    __slots__ = ("id", "label", "direction", "level", "polarity")
    ID_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    POLARITY_FIELD_NUMBER: _ClassVar[int]
    id: int
    label: str
    direction: PinDirection
    level: SignalLevel
    polarity: ActivePolarity
    def __init__(self, id: _Optional[int] = ..., label: _Optional[str] = ..., direction: _Optional[_Union[PinDirection, str]] = ..., level: _Optional[_Union[SignalLevel, str]] = ..., polarity: _Optional[_Union[ActivePolarity, str]] = ...) -> None: ...

class PinChange(_message.Message):
    __slots__ = ("pin", "level", "microseconds", "sequence")
    PIN_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    MICROSECONDS_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    pin: int
    level: SignalLevel
    microseconds: int
    sequence: int
    def __init__(self, pin: _Optional[int] = ..., level: _Optional[_Union[SignalLevel, str]] = ..., microseconds: _Optional[int] = ..., sequence: _Optional[int] = ...) -> None: ...

class JournalEntry(_message.Message):
    __slots__ = ("function", "microseconds", "sequence")
    FUNCTION_FIELD_NUMBER: _ClassVar[int]
    MICROSECONDS_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    function: str
    microseconds: int
    sequence: int
    def __init__(self, function: _Optional[str] = ..., microseconds: _Optional[int] = ..., sequence: _Optional[int] = ...) -> None: ...

class Signal(_message.Message):
    __slots__ = ("waveform", "amplitude", "offset", "frequency_hz", "phase_degrees")
    WAVEFORM_FIELD_NUMBER: _ClassVar[int]
    AMPLITUDE_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    FREQUENCY_HZ_FIELD_NUMBER: _ClassVar[int]
    PHASE_DEGREES_FIELD_NUMBER: _ClassVar[int]
    waveform: Waveform
    amplitude: float
    offset: float
    frequency_hz: float
    phase_degrees: float
    def __init__(self, waveform: _Optional[_Union[Waveform, str]] = ..., amplitude: _Optional[float] = ..., offset: _Optional[float] = ..., frequency_hz: _Optional[float] = ..., phase_degrees: _Optional[float] = ...) -> None: ...

class Channel(_message.Message):
    __slots__ = ("id", "label", "unit", "direction", "value", "signal", "has_value")
    ID_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    UNIT_FIELD_NUMBER: _ClassVar[int]
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    SIGNAL_FIELD_NUMBER: _ClassVar[int]
    HAS_VALUE_FIELD_NUMBER: _ClassVar[int]
    id: int
    label: str
    unit: str
    direction: ChannelDirection
    value: float
    signal: Signal
    has_value: bool
    def __init__(self, id: _Optional[int] = ..., label: _Optional[str] = ..., unit: _Optional[str] = ..., direction: _Optional[_Union[ChannelDirection, str]] = ..., value: _Optional[float] = ..., signal: _Optional[_Union[Signal, _Mapping]] = ..., has_value: _Optional[bool] = ...) -> None: ...

class Image(_message.Message):
    __slots__ = ("runtime_base", "size", "executable")
    RUNTIME_BASE_FIELD_NUMBER: _ClassVar[int]
    SIZE_FIELD_NUMBER: _ClassVar[int]
    EXECUTABLE_FIELD_NUMBER: _ClassVar[int]
    runtime_base: int
    size: int
    executable: str
    def __init__(self, runtime_base: _Optional[int] = ..., size: _Optional[int] = ..., executable: _Optional[str] = ...) -> None: ...

class Watch(_message.Message):
    __slots__ = ("channel", "path", "address", "encoding", "byte_width", "writable", "value", "bit_offset", "bit_width")
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    ENCODING_FIELD_NUMBER: _ClassVar[int]
    BYTE_WIDTH_FIELD_NUMBER: _ClassVar[int]
    WRITABLE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    BIT_OFFSET_FIELD_NUMBER: _ClassVar[int]
    BIT_WIDTH_FIELD_NUMBER: _ClassVar[int]
    channel: int
    path: str
    address: int
    encoding: VariableEncoding
    byte_width: int
    writable: bool
    value: float
    bit_offset: int
    bit_width: int
    def __init__(self, channel: _Optional[int] = ..., path: _Optional[str] = ..., address: _Optional[int] = ..., encoding: _Optional[_Union[VariableEncoding, str]] = ..., byte_width: _Optional[int] = ..., writable: _Optional[bool] = ..., value: _Optional[float] = ..., bit_offset: _Optional[int] = ..., bit_width: _Optional[int] = ...) -> None: ...

class BusAddress(_message.Message):
    __slots__ = ("value", "extended")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    EXTENDED_FIELD_NUMBER: _ClassVar[int]
    value: int
    extended: bool
    def __init__(self, value: _Optional[int] = ..., extended: _Optional[bool] = ...) -> None: ...

class Bus(_message.Message):
    __slots__ = ("id", "kind", "label", "bitrate_bps")
    ID_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    BITRATE_BPS_FIELD_NUMBER: _ClassVar[int]
    id: int
    kind: BusKind
    label: str
    bitrate_bps: int
    def __init__(self, id: _Optional[int] = ..., kind: _Optional[_Union[BusKind, str]] = ..., label: _Optional[str] = ..., bitrate_bps: _Optional[int] = ...) -> None: ...

class Component(_message.Message):
    __slots__ = ("bus", "address", "label", "model", "properties")
    BUS_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    bus: int
    address: BusAddress
    label: str
    model: str
    properties: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, bus: _Optional[int] = ..., address: _Optional[_Union[BusAddress, _Mapping]] = ..., label: _Optional[str] = ..., model: _Optional[str] = ..., properties: _Optional[_Iterable[int]] = ...) -> None: ...

class BusRecord(_message.Message):
    __slots__ = ("bus", "kind", "direction", "address", "payload", "response", "accepted", "microseconds", "sequence")
    BUS_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    RESPONSE_FIELD_NUMBER: _ClassVar[int]
    ACCEPTED_FIELD_NUMBER: _ClassVar[int]
    MICROSECONDS_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    bus: int
    kind: BusKind
    direction: BusDirection
    address: BusAddress
    payload: bytes
    response: bytes
    accepted: bool
    microseconds: int
    sequence: int
    def __init__(self, bus: _Optional[int] = ..., kind: _Optional[_Union[BusKind, str]] = ..., direction: _Optional[_Union[BusDirection, str]] = ..., address: _Optional[_Union[BusAddress, _Mapping]] = ..., payload: _Optional[bytes] = ..., response: _Optional[bytes] = ..., accepted: _Optional[bool] = ..., microseconds: _Optional[int] = ..., sequence: _Optional[int] = ...) -> None: ...

class Timing(_message.Message):
    __slots__ = ("function", "calls", "answered_calls", "total_nanoseconds", "shortest_nanoseconds", "longest_nanoseconds", "bands")
    FUNCTION_FIELD_NUMBER: _ClassVar[int]
    CALLS_FIELD_NUMBER: _ClassVar[int]
    ANSWERED_CALLS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_NANOSECONDS_FIELD_NUMBER: _ClassVar[int]
    SHORTEST_NANOSECONDS_FIELD_NUMBER: _ClassVar[int]
    LONGEST_NANOSECONDS_FIELD_NUMBER: _ClassVar[int]
    BANDS_FIELD_NUMBER: _ClassVar[int]
    function: str
    calls: int
    answered_calls: int
    total_nanoseconds: int
    shortest_nanoseconds: int
    longest_nanoseconds: int
    bands: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, function: _Optional[str] = ..., calls: _Optional[int] = ..., answered_calls: _Optional[int] = ..., total_nanoseconds: _Optional[int] = ..., shortest_nanoseconds: _Optional[int] = ..., longest_nanoseconds: _Optional[int] = ..., bands: _Optional[_Iterable[int]] = ...) -> None: ...

class ProfilePath(_message.Message):
    __slots__ = ("address", "parent", "calls", "total_nanoseconds", "self_nanoseconds")
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    PARENT_FIELD_NUMBER: _ClassVar[int]
    CALLS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_NANOSECONDS_FIELD_NUMBER: _ClassVar[int]
    SELF_NANOSECONDS_FIELD_NUMBER: _ClassVar[int]
    address: int
    parent: int
    calls: int
    total_nanoseconds: int
    self_nanoseconds: int
    def __init__(self, address: _Optional[int] = ..., parent: _Optional[int] = ..., calls: _Optional[int] = ..., total_nanoseconds: _Optional[int] = ..., self_nanoseconds: _Optional[int] = ...) -> None: ...

class Profile(_message.Message):
    __slots__ = ("address", "calls", "total_nanoseconds", "self_nanoseconds", "longest_nanoseconds", "frame_bytes")
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    CALLS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_NANOSECONDS_FIELD_NUMBER: _ClassVar[int]
    SELF_NANOSECONDS_FIELD_NUMBER: _ClassVar[int]
    LONGEST_NANOSECONDS_FIELD_NUMBER: _ClassVar[int]
    FRAME_BYTES_FIELD_NUMBER: _ClassVar[int]
    address: int
    calls: int
    total_nanoseconds: int
    self_nanoseconds: int
    longest_nanoseconds: int
    frame_bytes: int
    def __init__(self, address: _Optional[int] = ..., calls: _Optional[int] = ..., total_nanoseconds: _Optional[int] = ..., self_nanoseconds: _Optional[int] = ..., longest_nanoseconds: _Optional[int] = ..., frame_bytes: _Optional[int] = ...) -> None: ...

class HeapSite(_message.Message):
    __slots__ = ("site", "blocks", "bytes")
    SITE_FIELD_NUMBER: _ClassVar[int]
    BLOCKS_FIELD_NUMBER: _ClassVar[int]
    BYTES_FIELD_NUMBER: _ClassVar[int]
    site: int
    blocks: int
    bytes: int
    def __init__(self, site: _Optional[int] = ..., blocks: _Optional[int] = ..., bytes: _Optional[int] = ...) -> None: ...

class Heap(_message.Message):
    __slots__ = ("allocations", "frees", "failures", "live_bytes", "peak_bytes", "untracked_blocks", "is_watched", "outstanding")
    ALLOCATIONS_FIELD_NUMBER: _ClassVar[int]
    FREES_FIELD_NUMBER: _ClassVar[int]
    FAILURES_FIELD_NUMBER: _ClassVar[int]
    LIVE_BYTES_FIELD_NUMBER: _ClassVar[int]
    PEAK_BYTES_FIELD_NUMBER: _ClassVar[int]
    UNTRACKED_BLOCKS_FIELD_NUMBER: _ClassVar[int]
    IS_WATCHED_FIELD_NUMBER: _ClassVar[int]
    OUTSTANDING_FIELD_NUMBER: _ClassVar[int]
    allocations: int
    frees: int
    failures: int
    live_bytes: int
    peak_bytes: int
    untracked_blocks: int
    is_watched: bool
    outstanding: _containers.RepeatedCompositeFieldContainer[HeapSite]
    def __init__(self, allocations: _Optional[int] = ..., frees: _Optional[int] = ..., failures: _Optional[int] = ..., live_bytes: _Optional[int] = ..., peak_bytes: _Optional[int] = ..., untracked_blocks: _Optional[int] = ..., is_watched: _Optional[bool] = ..., outstanding: _Optional[_Iterable[_Union[HeapSite, _Mapping]]] = ...) -> None: ...

class Sample(_message.Message):
    __slots__ = ("channel", "microseconds", "value", "sequence")
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    MICROSECONDS_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    channel: int
    microseconds: int
    value: float
    sequence: int
    def __init__(self, channel: _Optional[int] = ..., microseconds: _Optional[int] = ..., value: _Optional[float] = ..., sequence: _Optional[int] = ...) -> None: ...

class Request(_message.Message):
    __slots__ = ("id", "command", "pin", "level", "microseconds", "channel", "signal", "after_sequence", "address", "encoding", "byte_width", "path", "writable", "bit_offset", "bit_width", "value", "bus", "bus_address", "payload", "label", "watching")
    ID_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    PIN_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    MICROSECONDS_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    SIGNAL_FIELD_NUMBER: _ClassVar[int]
    AFTER_SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    ENCODING_FIELD_NUMBER: _ClassVar[int]
    BYTE_WIDTH_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    WRITABLE_FIELD_NUMBER: _ClassVar[int]
    BIT_OFFSET_FIELD_NUMBER: _ClassVar[int]
    BIT_WIDTH_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    BUS_FIELD_NUMBER: _ClassVar[int]
    BUS_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    WATCHING_FIELD_NUMBER: _ClassVar[int]
    id: int
    command: Command
    pin: int
    level: SignalLevel
    microseconds: int
    channel: int
    signal: Signal
    after_sequence: int
    address: int
    encoding: VariableEncoding
    byte_width: int
    path: str
    writable: bool
    bit_offset: int
    bit_width: int
    value: float
    bus: int
    bus_address: BusAddress
    payload: bytes
    label: str
    watching: bool
    def __init__(self, id: _Optional[int] = ..., command: _Optional[_Union[Command, str]] = ..., pin: _Optional[int] = ..., level: _Optional[_Union[SignalLevel, str]] = ..., microseconds: _Optional[int] = ..., channel: _Optional[int] = ..., signal: _Optional[_Union[Signal, _Mapping]] = ..., after_sequence: _Optional[int] = ..., address: _Optional[int] = ..., encoding: _Optional[_Union[VariableEncoding, str]] = ..., byte_width: _Optional[int] = ..., path: _Optional[str] = ..., writable: _Optional[bool] = ..., bit_offset: _Optional[int] = ..., bit_width: _Optional[int] = ..., value: _Optional[float] = ..., bus: _Optional[int] = ..., bus_address: _Optional[_Union[BusAddress, _Mapping]] = ..., payload: _Optional[bytes] = ..., label: _Optional[str] = ..., watching: _Optional[bool] = ...) -> None: ...

class Response(_message.Message):
    __slots__ = ("protocol_version", "id", "status", "message", "microseconds", "time_mode", "pins", "journal", "firmware", "channels", "samples", "next_sequence", "image", "watches", "buses", "exchanges", "next_bus_sequence", "components", "timings", "profiles", "lost_profiles", "profiling", "stack_deepest_bytes", "stack_deepest_depth", "stack_path", "stack_path_complete", "heap", "pin_changes", "profile_paths", "lost_profile_paths", "watching_profile_paths")
    PROTOCOL_VERSION_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    MICROSECONDS_FIELD_NUMBER: _ClassVar[int]
    TIME_MODE_FIELD_NUMBER: _ClassVar[int]
    PINS_FIELD_NUMBER: _ClassVar[int]
    JOURNAL_FIELD_NUMBER: _ClassVar[int]
    FIRMWARE_FIELD_NUMBER: _ClassVar[int]
    CHANNELS_FIELD_NUMBER: _ClassVar[int]
    SAMPLES_FIELD_NUMBER: _ClassVar[int]
    NEXT_SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    IMAGE_FIELD_NUMBER: _ClassVar[int]
    WATCHES_FIELD_NUMBER: _ClassVar[int]
    BUSES_FIELD_NUMBER: _ClassVar[int]
    EXCHANGES_FIELD_NUMBER: _ClassVar[int]
    NEXT_BUS_SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    COMPONENTS_FIELD_NUMBER: _ClassVar[int]
    TIMINGS_FIELD_NUMBER: _ClassVar[int]
    PROFILES_FIELD_NUMBER: _ClassVar[int]
    LOST_PROFILES_FIELD_NUMBER: _ClassVar[int]
    PROFILING_FIELD_NUMBER: _ClassVar[int]
    STACK_DEEPEST_BYTES_FIELD_NUMBER: _ClassVar[int]
    STACK_DEEPEST_DEPTH_FIELD_NUMBER: _ClassVar[int]
    STACK_PATH_FIELD_NUMBER: _ClassVar[int]
    STACK_PATH_COMPLETE_FIELD_NUMBER: _ClassVar[int]
    HEAP_FIELD_NUMBER: _ClassVar[int]
    PIN_CHANGES_FIELD_NUMBER: _ClassVar[int]
    PROFILE_PATHS_FIELD_NUMBER: _ClassVar[int]
    LOST_PROFILE_PATHS_FIELD_NUMBER: _ClassVar[int]
    WATCHING_PROFILE_PATHS_FIELD_NUMBER: _ClassVar[int]
    protocol_version: int
    id: int
    status: Status
    message: str
    microseconds: int
    time_mode: TimeMode
    pins: _containers.RepeatedCompositeFieldContainer[Pin]
    journal: _containers.RepeatedCompositeFieldContainer[JournalEntry]
    firmware: str
    channels: _containers.RepeatedCompositeFieldContainer[Channel]
    samples: _containers.RepeatedCompositeFieldContainer[Sample]
    next_sequence: int
    image: Image
    watches: _containers.RepeatedCompositeFieldContainer[Watch]
    buses: _containers.RepeatedCompositeFieldContainer[Bus]
    exchanges: _containers.RepeatedCompositeFieldContainer[BusRecord]
    next_bus_sequence: int
    components: _containers.RepeatedCompositeFieldContainer[Component]
    timings: _containers.RepeatedCompositeFieldContainer[Timing]
    profiles: _containers.RepeatedCompositeFieldContainer[Profile]
    lost_profiles: int
    profiling: bool
    stack_deepest_bytes: int
    stack_deepest_depth: int
    stack_path: _containers.RepeatedScalarFieldContainer[int]
    stack_path_complete: bool
    heap: Heap
    pin_changes: _containers.RepeatedCompositeFieldContainer[PinChange]
    profile_paths: _containers.RepeatedCompositeFieldContainer[ProfilePath]
    lost_profile_paths: int
    watching_profile_paths: bool
    def __init__(self, protocol_version: _Optional[int] = ..., id: _Optional[int] = ..., status: _Optional[_Union[Status, str]] = ..., message: _Optional[str] = ..., microseconds: _Optional[int] = ..., time_mode: _Optional[_Union[TimeMode, str]] = ..., pins: _Optional[_Iterable[_Union[Pin, _Mapping]]] = ..., journal: _Optional[_Iterable[_Union[JournalEntry, _Mapping]]] = ..., firmware: _Optional[str] = ..., channels: _Optional[_Iterable[_Union[Channel, _Mapping]]] = ..., samples: _Optional[_Iterable[_Union[Sample, _Mapping]]] = ..., next_sequence: _Optional[int] = ..., image: _Optional[_Union[Image, _Mapping]] = ..., watches: _Optional[_Iterable[_Union[Watch, _Mapping]]] = ..., buses: _Optional[_Iterable[_Union[Bus, _Mapping]]] = ..., exchanges: _Optional[_Iterable[_Union[BusRecord, _Mapping]]] = ..., next_bus_sequence: _Optional[int] = ..., components: _Optional[_Iterable[_Union[Component, _Mapping]]] = ..., timings: _Optional[_Iterable[_Union[Timing, _Mapping]]] = ..., profiles: _Optional[_Iterable[_Union[Profile, _Mapping]]] = ..., lost_profiles: _Optional[int] = ..., profiling: _Optional[bool] = ..., stack_deepest_bytes: _Optional[int] = ..., stack_deepest_depth: _Optional[int] = ..., stack_path: _Optional[_Iterable[int]] = ..., stack_path_complete: _Optional[bool] = ..., heap: _Optional[_Union[Heap, _Mapping]] = ..., pin_changes: _Optional[_Iterable[_Union[PinChange, _Mapping]]] = ..., profile_paths: _Optional[_Iterable[_Union[ProfilePath, _Mapping]]] = ..., lost_profile_paths: _Optional[int] = ..., watching_profile_paths: _Optional[bool] = ...) -> None: ...
