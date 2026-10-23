"""Components a client takes the part of.

Two of the four buses have no master waiting inside a call, so a peer on
them can live in the client. What that buys is a test fixture written in
Python; what it costs is latency, and the shape of the thing has to make
both obvious.
"""

from __future__ import annotations

import pytest
from simulation_doubles import RecordingSession

from looper.application.components import BusComponent, ComponentHost, frames_addressed_to
from looper.domain.model.simulation import (
    BusAddress,
    BusDirection,
    BusKind,
    BusTraceEntry,
)

NODE_ADDRESS = BusAddress(BusKind.CAN, 0x500)
PUBLISHED_ADDRESS = BusAddress(BusKind.CAN, 0x701)


class Recorder(BusComponent):
    """A peer that remembers what it saw and answers when told to."""

    def __init__(self, bus: int = 2, reply: bytes | None = None) -> None:
        super().__init__(bus, NODE_ADDRESS, "Recorder")
        self.seen: list[BusTraceEntry] = []
        self._reply = reply

    def on_exchange(self, exchange: BusTraceEntry) -> None:
        self.seen.append(exchange)
        if self._reply is not None:
            self.send(self._reply)


def an_exchange(
    sequence: int,
    bus: int = 2,
    address: BusAddress = PUBLISHED_ADDRESS,
    direction: BusDirection = BusDirection.OUTBOUND,
) -> BusTraceEntry:
    """One recorded CAN frame."""
    return BusTraceEntry(
        bus=bus,
        kind=BusKind.CAN,
        direction=direction,
        address=address,
        payload=b"\x01\x02",
        sequence=sequence,
    )


class Anywhere(BusComponent):
    """A peer that will try to sit on any bus it is given."""

    def on_exchange(self, exchange: BusTraceEntry) -> None:
        """Nothing: this one exists to be constructed, or refused."""


def test_a_peer_on_a_bus_the_firmware_masters_is_refused() -> None:
    """Nothing on the other end of a channel can answer inside the call."""
    for kind in (BusKind.SPI, BusKind.I2C):
        with pytest.raises(ValueError, match="cannot take a peer's part"):
            Anywhere(0, BusAddress(kind, 0), "no")

    assert Anywhere(3, BusAddress(BusKind.UART, 0), "terminal").label == "terminal"


def test_attaching_tells_the_simulation_where_the_peer_sits() -> None:
    session = RecordingSession()
    host = ComponentHost(session)

    host.attach(Recorder())

    assert session.attached == [(2, NODE_ADDRESS, "Recorder")]


def test_what_crossed_reaches_the_peer_on_that_bus() -> None:
    session = RecordingSession()
    session.exchanges = (an_exchange(0), an_exchange(1))
    recorder = Recorder()
    host = ComponentHost(session)
    host.attach(recorder)

    handed = host.poll()

    assert handed == 2
    assert [one.sequence for one in recorder.seen] == [0, 1]


def test_a_peer_only_sees_its_own_bus() -> None:
    session = RecordingSession()
    session.exchanges = (an_exchange(0, bus=2), an_exchange(1, bus=3))
    recorder = Recorder(bus=2)
    host = ComponentHost(session)
    host.attach(recorder)

    host.poll()

    assert [one.bus for one in recorder.seen] == [2]


def test_a_second_pass_brings_only_what_is_new() -> None:
    session = RecordingSession()
    session.exchanges = (an_exchange(0),)
    recorder = Recorder()
    host = ComponentHost(session)
    host.attach(recorder)
    host.poll()

    session.exchanges = (an_exchange(0), an_exchange(1))
    host.poll()

    assert [one.sequence for one in recorder.seen] == [0, 1]


def test_a_peer_answers_by_putting_something_back() -> None:
    session = RecordingSession()
    session.exchanges = (an_exchange(0),)
    host = ComponentHost(session)
    host.attach(Recorder(reply=b"\xaa\xbb"))

    host.poll()

    bus, message = session.sent[0]
    assert (bus, message.address, message.payload) == (2, NODE_ADDRESS, b"\xaa\xbb")


def test_a_peer_that_is_not_attached_cannot_answer() -> None:
    with pytest.raises(RuntimeError, match="not attached"):
        Recorder().send(b"\x01")


def test_letting_go_takes_the_peer_off_the_bus() -> None:
    session = RecordingSession()
    recorder = Recorder()

    with ComponentHost(session) as host:
        host.attach(recorder)

    assert session.detached == [(2, NODE_ADDRESS)]


def test_a_detached_peer_can_no_longer_answer() -> None:
    session = RecordingSession()
    recorder = Recorder()
    host = ComponentHost(session)
    host.attach(recorder)

    host.detach(recorder)

    with pytest.raises(RuntimeError, match="not attached"):
        recorder.send(b"\x01")


def test_a_peer_answers_only_what_the_firmware_sent_it() -> None:
    """Answering its own reply coming back round would loop."""
    mine = BusAddress(BusKind.CAN, 0x500)
    exchanges = iter(
        (
            an_exchange(0, address=mine),
            an_exchange(1, address=mine, direction=BusDirection.INBOUND),
            an_exchange(2, address=PUBLISHED_ADDRESS),
        )
    )

    kept = tuple(frames_addressed_to(exchanges, mine))

    assert [one.sequence for one in kept] == [0]
