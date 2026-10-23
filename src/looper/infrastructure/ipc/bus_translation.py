"""Translation between the bus messages of the protocol and the domain model."""

from __future__ import annotations

from looper.domain.model.simulation import (
    BusAddress,
    BusDirection,
    BusKind,
    BusMessage,
    BusTraceEntry,
    ComponentDescription,
    SimulatedBus,
)
from looper.infrastructure.ipc.generated import looper_control_pb2 as protocol

BUS_KINDS: dict[int, BusKind] = {
    protocol.BUS_KIND_SPI: BusKind.SPI,
    protocol.BUS_KIND_I2C: BusKind.I2C,
    protocol.BUS_KIND_UART: BusKind.UART,
    protocol.BUS_KIND_CAN: BusKind.CAN,
}
BUS_KINDS_TO_PROTOCOL: dict[BusKind, int] = {kind: value for value, kind in BUS_KINDS.items()}
BUS_DIRECTIONS: dict[int, BusDirection] = {
    protocol.BUS_DIRECTION_OUTBOUND: BusDirection.OUTBOUND,
    protocol.BUS_DIRECTION_INBOUND: BusDirection.INBOUND,
}


def to_bus(bus: protocol.Bus) -> SimulatedBus:
    """Translate one protocol bus into its domain representation.

    An unset kind is read as CAN, which is the only kind a client can put
    something on without a component answering, and so the safest reading.
    """
    return SimulatedBus(
        identifier=bus.id,
        kind=BUS_KINDS.get(bus.kind, BusKind.CAN),
        label=bus.label,
        bitrate_bps=bus.bitrate_bps,
    )


def to_bus_address(address: protocol.BusAddress, kind: BusKind) -> BusAddress:
    """Translate one protocol address into its domain representation.

    The kind does not travel with the address inside a record, because the
    record already says which bus it crossed; it is passed in here instead.
    """
    return BusAddress(kind=kind, value=address.value, is_extended=address.extended)


def from_bus_address(address: BusAddress) -> protocol.BusAddress:
    """Translate a domain address into the protocol message."""
    return protocol.BusAddress(value=address.value, extended=address.is_extended)


def to_component(component: protocol.Component, kind: BusKind) -> ComponentDescription:
    """Translate one listed component into its domain representation.

    A component message says which bus it is on but not what kind of bus
    that is, because the bus listing already says so. The caller resolves
    it there and passes it in, rather than the simulation repeating itself
    once per component.
    """
    return ComponentDescription(
        bus=component.bus,
        address=to_bus_address(component.address, kind),
        label=component.label,
        model=component.model,
        properties=tuple(component.properties),
    )


def to_bus_trace_entry(record: protocol.BusRecord) -> BusTraceEntry:
    """Translate one recorded exchange into its domain representation.

    A record nothing accepted is kept rather than dropped: a client that
    sent something and saw no reaction needs to tell a refused exchange from
    one that never happened.
    """
    kind = BUS_KINDS.get(record.kind, BusKind.CAN)
    return BusTraceEntry(
        bus=record.bus,
        kind=kind,
        direction=BUS_DIRECTIONS.get(record.direction, BusDirection.OUTBOUND),
        address=to_bus_address(record.address, kind),
        payload=bytes(record.payload),
        response=bytes(record.response),
        accepted=record.accepted,
        microseconds=record.microseconds,
        sequence=record.sequence,
    )


def from_bus_message(message: BusMessage) -> tuple[protocol.BusAddress, bytes]:
    """Translate a domain message into the two fields a request carries."""
    return from_bus_address(message.address), message.payload


def bus_kind_to_protocol(kind: BusKind) -> int:
    """Translate a domain bus kind into its protocol value."""
    return BUS_KINDS_TO_PROTOCOL[kind]
