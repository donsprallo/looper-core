"""Naming the parties of a bus conversation.

The domain arranges the exchanges; what is left is what to call the
columns. A chip select number is what the firmware uses and not what
a reader remembers, so a column is named after the component that
answers there when one does.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from looper.application.dto.ladder_view import LadderView, PartyView, StepView
from looper.domain.model.simulation import BusAddress, BusTraceEntry, ComponentDescription
from looper.domain.services import Conversation, Turn, conversation_of

#: Said of a bus where everything addressed was taken.
#:
#: Taken rather than answered, because that is what is measured.
#: On SPI and I2C a component took the exchange and replied inside
#: it; on CAN a controller's filters took the frame and nobody
#: replied to anything. The two are the same fact: something on the
#: bus was there.
EVERYTHING_TAKEN = "Everything that was addressed was taken."

#: Said when something was not. The parties are named beside their
#: columns as well; this is the line that makes a reader look.
NOTHING_TOOK = "addressed, and nothing took what was sent"


def build_ladder_view(
    bus_name: str,
    exchanges: Sequence[BusTraceEntry],
    components: Sequence[ComponentDescription] = (),
) -> LadderView:
    """Arrange one bus into a ladder and name its columns."""
    spoken = conversation_of(exchanges)
    named = {one.address: one.label for one in components}
    return LadderView(
        bus_name=bus_name,
        parties=tuple(_party(one, named, spoken) for one in spoken.addresses),
        steps=tuple(_step(one, spoken) for one in spoken.turns),
        note=_note(spoken, named),
    )


def _party(address: BusAddress, named: Mapping[BusAddress, str], spoken: Conversation) -> PartyView:
    """One column, named after whatever answers there."""
    return PartyView(
        address=address.text,
        name=named.get(address, _place(address)),
        is_silent=address in spoken.silent_addresses,
    )


def _place(address: BusAddress) -> str:
    """Where on the bus this is, for a column nothing answers at.

    The bare number is what the firmware uses and not what a reader
    remembers. A heading says what kind of place it is, because a
    column headed `1` could be a chip select, a port or a device.
    """
    return f"{address.kind.address_name} {address.text}"


def _step(turn: Turn, spoken: Conversation) -> StepView:
    """One exchange, as a line between two columns."""
    return StepView(
        seconds=turn.seconds,
        gap=_gap_text(turn.gap_seconds),
        column=spoken.column_of(turn.address),
        is_outbound=turn.is_outbound,
        payload=_hex(turn.exchange.payload),
        response=_hex(turn.exchange.response),
        was_taken=turn.was_taken,
    )


def _note(spoken: Conversation, named: Mapping[BusAddress, str]) -> str:
    """What is worth saying about the bus as a whole."""
    silent = spoken.silent_addresses
    if spoken.is_empty:
        return ""
    if not silent:
        return EVERYTHING_TAKEN
    names = ", ".join(named.get(one, _place(one)) for one in silent)
    return f"{names}: {NOTHING_TOOK}"


def _hex(payload: bytes) -> str:
    """Bytes as a person reads them."""
    return " ".join(f"{one:02X}" for one in payload)


def _gap_text(seconds: float) -> str:
    """How long since the previous turn, or nothing for the first."""
    if seconds <= 0.0:
        return ""
    if seconds < 1e-3:
        return f"+{seconds * 1e6:.0f} us"
    if seconds < 1.0:
        return f"+{seconds * 1e3:.1f} ms"
    return f"+{seconds:.2f} s"
