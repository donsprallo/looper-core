"""Components a client takes the part of, rather than the simulation.

Most components are C, because they answer while the firmware is inside the
call that asked: a converter sampling at eight kilohertz leaves no room for
a round trip. Two of the four buses are different. A CAN node and a UART
peer speak when they have something to say, and nobody is waiting inside a
call, so they can live here instead -- which is a far nicer place to write
a test fixture that replays a log or answers a command.

What that costs is latency, and it is worth being plain about it: such a
component learns what crossed from the recording and answers on the next
poll, so it reacts in tens of milliseconds rather than microseconds. For a
peer that would answer in milliseconds anyway this changes nothing; for one
the firmware times out on in under a millisecond, write it in C.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Iterator

from looper.domain.model.simulation import (
    BusAddress,
    BusDirection,
    BusKind,
    BusMessage,
    BusTraceEntry,
)
from looper.domain.ports import SimulationSession

DEFAULT_INTERVAL_SECONDS = 0.02

#: Kinds a client can take a peer's part on. On the other two the firmware
#: is the master and expects an answer inside the call it made.
HOSTABLE_KINDS = (BusKind.CAN, BusKind.UART)


class _Sender:
    """What a component calls to put something on its bus."""

    def __init__(self, session: SimulationSession, bus: int) -> None:
        self._session = session
        self._bus = bus

    def __call__(self, message: BusMessage) -> None:
        self._session.send_bus_message(self._bus, message)


class BusComponent(ABC):
    """A peer on a bus, simulated in the client.

    Attributes:
        bus: Bus the peer is attached to.
        address: Where on that bus it answers.
        label: What it is called in the listing.
    """

    def __init__(self, bus: int, address: BusAddress, label: str) -> None:
        if address.kind not in HOSTABLE_KINDS:
            raise ValueError(
                f"The firmware is the master on a {address.kind.value} bus, so a "
                f"client cannot take a peer's part there"
            )
        self.bus = bus
        self.address = address
        self.label = label
        self._send: _Sender | None = None

    @abstractmethod
    def on_exchange(self, exchange: BusTraceEntry) -> None:
        """React to something that crossed the bus this peer is on.

        Called for every exchange on its bus, outbound and inbound alike,
        in the order they were recorded. Reply with :meth:`send`.
        """

    def send(self, payload: bytes, address: BusAddress | None = None) -> None:
        """Put something on the bus, by default under this peer's address.

        Raises:
            RuntimeError: If the component is not attached to a host.
            ValueError: If the payload is too long for one message.
        """
        if self._send is None:
            raise RuntimeError(f"'{self.label}' is not attached to a simulation")
        self._send(BusMessage(address=address or self.address, payload=payload))

    def _bind(self, send: _Sender | None) -> None:
        """Give the component its way back onto the bus, or take it away."""
        self._send = send


class ComponentHost:
    """Attaches client side components and feeds them what crossed.

    One host serves any number of components across any number of buses. It
    reads the recording once per pass and hands each exchange to whatever is
    attached to that bus, which keeps the number of requests independent of
    the number of components.
    """

    def __init__(self, session: SimulationSession) -> None:
        self._session = session
        self._components: list[BusComponent] = []
        self._next_sequence = 0

    def attach(self, component: BusComponent) -> None:
        """Take the part of one peer, and begin from what crosses next.

        Raises:
            ValueError: If the simulation will not have it there.
        """
        self._session.attach_component(component.bus, component.address, component.label)
        component._bind(_Sender(self._session, component.bus))  # noqa: SLF001
        self._components.append(component)

    def detach(self, component: BusComponent) -> None:
        """Stop taking one peer's part."""
        self._session.detach_component(component.bus, component.address)
        component._bind(None)  # noqa: SLF001
        self._components.remove(component)

    def detach_all(self) -> None:
        """Stop taking every part, which a test teardown wants."""
        for component in tuple(self._components):
            self.detach(component)

    def poll(self) -> int:
        """Hand everything recorded since the last pass to its components.

        Returns:
            How many exchanges were handed on, counting one exchange once
            per component that saw it.
        """
        exchanges, self._next_sequence = self._session.read_bus_trace(self._next_sequence)
        handed = 0
        for exchange in exchanges:
            for component in self._components:
                if component.bus != exchange.bus:
                    continue
                component.on_exchange(exchange)
                handed += 1
        return handed

    def run(self, seconds: float | None = None, interval: float = DEFAULT_INTERVAL_SECONDS) -> None:
        """Poll until the time is up, or forever when no time is given."""
        deadline = None if seconds is None else time.monotonic() + seconds
        while (deadline is None) or (time.monotonic() < deadline):
            self.poll()
            time.sleep(interval)

    def __enter__(self) -> ComponentHost:
        return self

    def __exit__(self, *exception: object) -> None:
        self.detach_all()


def frames_addressed_to(
    exchanges: Iterator[BusTraceEntry], address: BusAddress
) -> Iterator[BusTraceEntry]:
    """Keep the exchanges a peer at one address would answer.

    What the firmware sent, under that address. An inbound exchange is this
    peer's own reply coming back round, and answering it would loop.
    """
    for exchange in exchanges:
        if (exchange.direction is BusDirection.OUTBOUND) and (exchange.address == address):
            yield exchange
