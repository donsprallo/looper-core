"""Mapping of bus state onto the client facing views."""

from __future__ import annotations

from looper.application.dto.bus_view import BusTraceView, BusView, ComponentView, ExchangeView
from looper.domain.model.simulation import BusTraceEntry, ComponentDescription, SimulatedBus


def build_bus_view(bus: SimulatedBus) -> BusView:
    """Translate one observed bus into its view."""
    return BusView(
        bus_id=bus.identifier,
        kind=bus.kind.value,
        name=bus.display_name,
        bitrate_bps=bus.bitrate_bps,
    )


def build_component_view(component: ComponentDescription) -> ComponentView:
    """Translate one listed component into its view."""
    return ComponentView(
        bus_id=component.bus,
        address=component.address.text,
        name=component.display_name,
        model=component.model,
        properties=component.properties,
    )


def build_bus_trace_view(entries: tuple[BusTraceEntry, ...], next_sequence: int) -> BusTraceView:
    """Translate a batch of recorded exchanges into its view."""
    return BusTraceView(
        exchanges=tuple(_build_exchange_view(entry) for entry in entries),
        next_sequence=next_sequence,
    )


def _build_exchange_view(entry: BusTraceEntry) -> ExchangeView:
    """Translate one recorded exchange into its view."""
    return ExchangeView(
        bus_id=entry.bus,
        kind=entry.kind.value,
        seconds=entry.seconds,
        direction=entry.direction.value,
        address=entry.address.text,
        length=entry.length,
        payload=entry.payload_text,
        response=entry.response_text,
        accepted=entry.accepted,
        sequence=entry.sequence,
    )
