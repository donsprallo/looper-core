"""A bus conversation, ready to be drawn as a ladder.

One column per party, time running down, and a line from one column
to another for each exchange. What a client needs beyond the records
themselves is who the columns are -- named after the component that
answers there, when one does, rather than after a chip select number
nobody remembers.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PartyView(BaseModel):
    """One column of the ladder.

    Attributes:
        address: Where on the bus it sits, as it is shown.
        name: What to call it: the component that answers there, or
            the address again when nothing does.
        is_silent: Whether it was addressed and never took
            anything, which is the finding a bus view exists for.
    """

    model_config = ConfigDict(frozen=True)

    address: str
    name: str
    is_silent: bool = False


class StepView(BaseModel):
    """One exchange, as a line between two columns.

    Attributes:
        seconds: When it happened.
        gap: How long since the previous step, as it is shown.
        column: Which party it was with, counting from zero.
        is_outbound: Whether the firmware started it, which is the
            direction the line is drawn in.
        payload: What the firmware sent, as hexadecimal pairs.
        response: What came back inside the same exchange, if any.
        was_taken: Whether anything on the bus took it.
    """

    model_config = ConfigDict(frozen=True)

    seconds: float
    gap: str
    column: int
    is_outbound: bool
    payload: str = ""
    response: str = ""
    was_taken: bool = True

    @property
    def was_answered(self) -> bool:
        """Whether something came back inside the exchange."""
        return bool(self.response)


class LadderView(BaseModel):
    """One bus, read as a conversation.

    Attributes:
        bus_name: What the firmware calls the bus.
        parties: The columns, in the order they were first addressed.
        steps: The exchanges, oldest first.
        note: What is worth saying about the whole of it, or empty.
    """

    model_config = ConfigDict(frozen=True)

    bus_name: str = ""
    parties: tuple[PartyView, ...] = ()
    steps: tuple[StepView, ...] = ()
    note: str = ""

    @property
    def is_empty(self) -> bool:
        """Whether nothing crossed this bus."""
        return not self.steps
