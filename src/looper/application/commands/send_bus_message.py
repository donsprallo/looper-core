"""Use case that puts one message on a simulated bus."""

from __future__ import annotations

from looper.domain.model.simulation import BusAddress, BusKind, BusMessage
from looper.domain.ports import SimulationSession


class SendBusMessage:
    """Puts one message on a bus for the firmware to receive.

    Whether the firmware is given it depends on the controller being
    simulated, whose filters the simulation applies. A message they turn
    away is still recorded, so a client that saw no reaction can tell which
    of the two happened.
    """

    def __init__(self, session: SimulationSession) -> None:
        self._session = session

    def execute(self, bus_id: int, message: BusMessage) -> None:
        """Send a message on a bus.

        Raises:
            ValueError: If the bus is unknown or is holding all it can.
        """
        self._session.send_bus_message(bus_id, message)

    def send_payload(
        self,
        bus_id: int,
        kind: BusKind,
        address: int,
        payload: bytes,
        extended: bool = False,
    ) -> None:
        """Send a message described by its parts, which is what a form offers.

        Raises:
            ValueError: If the kind of bus takes no messages, the address
                does not fit that kind, or the payload is too long for one
                message.
        """
        self.execute(
            bus_id,
            BusMessage(
                address=BusAddress(kind=kind, value=address, is_extended=extended),
                payload=payload,
            ),
        )
