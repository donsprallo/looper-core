"""What crossed a bus, read as a conversation rather than a list.

A table of exchanges is complete and almost unreadable. Every row
says the same four things in the same four columns, and the one
question a protocol raises -- who said what to whom, and what came
back -- has to be reassembled in the reader's head from the direction
column and the address column, row by row.

A conversation is the same records arranged by who was talking. One
column per party, time running down, and an exchange as a line from
one column to another. What that makes visible without being read:
which device is being addressed at all, whether anything answered,
and how long the firmware waited between turns.

The gap belongs here rather than in the drawing because it is the
part a reader cannot work out by looking: the rows of a ladder are
evenly spaced however far apart in time they were, so the time
between two turns has to be written down or it is lost.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from looper.domain.model.simulation import BusAddress, BusDirection, BusTraceEntry


@dataclass(frozen=True)
class Turn:
    """One exchange, placed in the conversation it belongs to.

    Attributes:
        exchange: The record as it was taken.
        gap_seconds: How long since the previous turn, zero for the
            first one there is nothing to measure from.
    """

    exchange: BusTraceEntry
    gap_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.gap_seconds < 0.0:
            raise ValueError("A conversation does not run backwards")

    @property
    def seconds(self) -> float:
        """When it happened."""
        return self.exchange.seconds

    @property
    def address(self) -> BusAddress:
        """Who the firmware was talking to, or who was talking to it."""
        return self.exchange.address

    @property
    def is_outbound(self) -> bool:
        """Whether the firmware started this one."""
        return self.exchange.direction is BusDirection.OUTBOUND

    @property
    def was_answered(self) -> bool:
        """Whether anything came back inside the same exchange.

        Only some kinds of bus answer at once -- SPI and I2C do,
        because the firmware is the master and waits inside its own
        call. On CAN an answer is a separate frame and a later turn.
        """
        return bool(self.exchange.response)

    @property
    def was_taken(self) -> bool:
        """Whether anything on the bus took it at all.

        False is the finding: the firmware spoke and nothing was
        there, or a controller's filters turned the frame away. The
        firmware was handed the zero value and believed it.
        """
        return self.exchange.accepted


@dataclass(frozen=True)
class Conversation:
    """Who was talking on one bus, and in what order.

    Attributes:
        addresses: Every party that was addressed, in the order they
            first appeared. The firmware is not among them: it is the
            one column every line starts or ends at.
        turns: The exchanges, oldest first.
    """

    addresses: tuple[BusAddress, ...] = field(default_factory=tuple)
    turns: tuple[Turn, ...] = field(default_factory=tuple)

    @property
    def is_empty(self) -> bool:
        """Whether nothing was said."""
        return not self.turns

    @property
    def silent_addresses(self) -> tuple[BusAddress, ...]:
        """The parties that were addressed and never took anything.

        A device the firmware talks to and that never answers is the
        single most useful thing a bus view can point at, and in a
        table it is spread over every row it appears in.
        """
        taken = {one.address for one in self.turns if one.was_taken}
        return tuple(one for one in self.addresses if one not in taken)

    def column_of(self, address: BusAddress) -> int:
        """Which column a party is drawn in, counting from zero."""
        return self.addresses.index(address)


def conversation_of(exchanges: Sequence[BusTraceEntry]) -> Conversation:
    """Arrange what crossed a bus by who was talking.

    Args:
        exchanges: What was recorded, oldest first.

    Returns:
        The conversation. Parties appear in the order they were first
        addressed rather than by address, so that the columns stay
        where they are as more is recorded.
    """
    if not exchanges:
        return Conversation()
    gaps = [0.0, *(_gap(earlier, later) for earlier, later in _consecutive(exchanges))]
    return Conversation(
        addresses=tuple(dict.fromkeys(one.address for one in exchanges)),
        turns=tuple(
            Turn(exchange=one, gap_seconds=gap) for one, gap in zip(exchanges, gaps, strict=True)
        ),
    )


def _consecutive(
    exchanges: Sequence[BusTraceEntry],
) -> tuple[tuple[BusTraceEntry, BusTraceEntry], ...]:
    """Every neighbouring pair."""
    return tuple(zip(exchanges, exchanges[1:], strict=False))


def _gap(earlier: BusTraceEntry, later: BusTraceEntry) -> float:
    """How long between two exchanges, never negative."""
    return max(0.0, later.seconds - earlier.seconds)
