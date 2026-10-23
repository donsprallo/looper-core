"""Mapping of firmware variables onto the client facing views."""

from __future__ import annotations

from looper.application.dto.variable_view import VariableView, WatchView
from looper.domain.model.firmware import (
    BitRange,
    FirmwareVariable,
    VariableEncoding,
    VariablePath,
    VariableWatch,
)


def build_variable_view(variable: FirmwareVariable, runtime_address: int) -> VariableView:
    """Translate one variable into its view.

    Args:
        variable: Variable as the debug information describes it.
        runtime_address: Where it sits in the process now.
    """
    return VariableView(
        path=variable.path.text,
        name=variable.path.leaf,
        root=variable.path.root,
        encoding=variable.encoding.value,
        byte_width=variable.byte_width,
        link_time_address=variable.link_time_address,
        runtime_address=runtime_address,
        is_writable=variable.is_writable,
        bit_offset=variable.bits.offset if variable.bits is not None else 0,
        bit_width=variable.bits.width if variable.bits is not None else 0,
        origin=variable.origin.value,
        declared_in=variable.declared_in,
    )


def to_firmware_variable(view: VariableView) -> FirmwareVariable:
    """Translate a listed variable back into the domain object.

    A client picks from a list and hands one entry back, so the trip out and
    in again has to arrive at the same variable it started from.
    """
    return FirmwareVariable(
        path=VariablePath(view.path),
        link_time_address=view.link_time_address,
        encoding=VariableEncoding(view.encoding),
        byte_width=view.byte_width,
        is_constant=not view.is_writable,
        bits=BitRange(view.bit_offset, view.bit_width) if view.is_bit_field else None,
    )


def build_watch_view(watch: VariableWatch) -> WatchView:
    """Translate one watch into its view."""
    return WatchView(
        channel_id=watch.channel,
        path=watch.variable.path.text,
        name=watch.variable.path.leaf,
        encoding=watch.variable.encoding.value,
        byte_width=watch.variable.byte_width,
        runtime_address=watch.runtime_address,
        is_writable=watch.is_drivable_by_client,
        value=watch.value,
        bit_offset=watch.variable.bits.offset if watch.variable.bits is not None else 0,
        bit_width=watch.variable.bits.width if watch.variable.bits is not None else 0,
    )
