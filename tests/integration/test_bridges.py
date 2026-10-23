"""Carrying a simulated bus over a real socket, in both directions.

Everything about a bridge that can be got wrong is at an edge: a frame
that arrived in two pieces, a connection nobody made, a reader that went
away. So this talks to a real simulation over real sockets rather than
to a double, and sends a frame split across two writes on purpose.
"""

from __future__ import annotations

import socket
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from bridge_fixture import (
    CAN_BASE_ID,
    CAN_BUS,
    OUTBOUND_BYTE,
    OUTBOUND_ID,
    UART_BUS,
    build_bridged_simulation,
    compiler_on_path,
)
from conftest import connect, free_port

from looper.infrastructure.ipc import ProtobufSimulationSession

READ_TIMEOUT_SECONDS = 5.0
POLL_SECONDS = 0.02
INBOUND_ID = 0x123
INBOUND_PAYLOAD = b"\xde\xad\xbe\xef"


def encode_frame(identifier: int, payload: bytes, extended: bool = False) -> bytes:
    """One CAN frame, in the layout looper_can_wire.h writes down."""
    return identifier.to_bytes(4, "little") + bytes([1 if extended else 0, len(payload)]) + payload


class Bridged:
    """A running bridged simulation and the ports it listens on."""

    def __init__(self, executable: Path) -> None:
        self.tcp_uart_port = free_port()
        self.tcp_can_port = free_port()
        self.udp_uart_port = free_port()
        self.control_port = free_port()
        self.process = subprocess.Popen(  # noqa: S603
            [
                str(executable),
                str(self.tcp_uart_port),
                str(self.tcp_can_port),
                str(self.udp_uart_port),
                "--port",
                str(self.control_port),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def stop(self) -> None:
        self.process.terminate()
        self.process.wait(timeout=READ_TIMEOUT_SECONDS)


@pytest.fixture(scope="module")
def bridged(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Bridged]:
    """One bridged simulation for the module."""
    compiler = compiler_on_path()
    if compiler is None:
        pytest.skip("no C compiler on PATH")
    executable = build_bridged_simulation(tmp_path_factory.mktemp("bridge"), compiler)
    running = Bridged(executable)
    try:
        yield running
    finally:
        running.stop()


def connected(port: int) -> socket.socket:
    """A TCP connection to a bridge, once it is listening."""
    deadline = time.monotonic() + READ_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            opened = socket.create_connection(("127.0.0.1", port), timeout=READ_TIMEOUT_SECONDS)
        except OSError:
            time.sleep(POLL_SECONDS)
            continue
        opened.settimeout(READ_TIMEOUT_SECONDS)
        return opened
    raise AssertionError(f"nothing ever listened on {port}")


def test_what_the_firmware_writes_reaches_a_tcp_reader(bridged: Bridged) -> None:
    with connected(bridged.tcp_uart_port) as reader:
        arrived = reader.recv(16)

    assert arrived
    assert set(arrived) == {OUTBOUND_BYTE}


def test_a_can_frame_arrives_whole_over_tcp(bridged: Bridged) -> None:
    with connected(bridged.tcp_can_port) as reader:
        arrived = reader.recv(6 * 8)

    identifier = int.from_bytes(arrived[0:4], "little")
    assert identifier == OUTBOUND_ID
    assert arrived[4] == 0
    assert arrived[5] == 2
    assert arrived[6:8] == b"\x11\x22"


def test_what_a_tcp_writer_sends_reaches_the_bus(bridged: Bridged) -> None:
    session = connect(bridged.control_port)
    session.clear_bus_trace()
    try:
        with connected(bridged.tcp_can_port) as writer:
            writer.sendall(encode_frame(INBOUND_ID, INBOUND_PAYLOAD))
            assert _waits_for_frame(session, INBOUND_ID) == INBOUND_PAYLOAD
    finally:
        session.close()


def test_a_frame_split_across_two_writes_still_arrives_whole(bridged: Bridged) -> None:
    """A stream hands over what it has, which is not what was written."""
    session = connect(bridged.control_port)
    encoded = encode_frame(0x456, b"\x01\x02\x03")
    try:
        with connected(bridged.tcp_can_port) as writer:
            writer.sendall(encoded[:3])
            time.sleep(0.1)
            writer.sendall(encoded[3:])
            assert _waits_for_frame(session, 0x456) == b"\x01\x02\x03"
    finally:
        session.close()


def test_two_frames_in_one_write_both_arrive(bridged: Bridged) -> None:
    session = connect(bridged.control_port)
    session.clear_bus_trace()
    try:
        with connected(bridged.tcp_can_port) as writer:
            writer.sendall(encode_frame(0x201, b"\x0a") + encode_frame(0x202, b"\x0b"))
            assert _waits_for_frame(session, 0x201) == b"\x0a"
            assert _waits_for_frame(session, 0x202) == b"\x0b"
    finally:
        session.close()


def test_a_udp_writer_reaches_the_bus_and_is_answered(bridged: Bridged) -> None:
    """With no peer configured, the bridge answers whoever wrote to it."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as peer:
        peer.settimeout(READ_TIMEOUT_SECONDS)
        peer.sendto(b"hello", ("127.0.0.1", bridged.udp_uart_port))
        answered, _ = peer.recvfrom(64)

    assert set(answered) == {OUTBOUND_BYTE}


def test_the_bridges_are_listed_as_what_is_on_the_bus(bridged: Bridged) -> None:
    session = connect(bridged.control_port)
    try:
        attached = {one.label: one.model for one in session.read_components()}
    finally:
        session.close()

    assert attached["Console"] == "tcp"
    assert attached["Gateway"] == "tcp"
    assert attached["Telemetry"] == "udp"


def test_a_bridge_with_nobody_connected_is_not_a_failure(bridged: Bridged) -> None:
    """A wire with nothing plugged in is the ordinary state of a wire."""
    session = connect(bridged.control_port)
    try:
        before = session.read_time().microseconds
        time.sleep(0.2)
        assert session.read_time().microseconds > before
    finally:
        session.close()


def _waits_for_frame(session: ProtobufSimulationSession, identifier: int) -> bytes:
    """The payload of the next frame carrying an identifier.

    Paged by the last record seen rather than by the sequence the reply
    reports as next: that one is where the recording has got to, not
    where this reader has, and following it would step over everything
    in between.
    """
    deadline = time.monotonic() + READ_TIMEOUT_SECONDS
    seen = 0
    while time.monotonic() < deadline:
        exchanges, _ = session.read_bus_trace(seen)
        for exchange in exchanges:
            if (exchange.bus == CAN_BUS) and (exchange.address.value == identifier):
                return exchange.payload
        if exchanges:
            seen = exchanges[-1].sequence + 1
        time.sleep(POLL_SECONDS)
    raise AssertionError(f"no frame {identifier:#x} ever reached bus {CAN_BUS}")


def test_the_uart_bus_is_the_one_that_was_bridged(bridged: Bridged) -> None:
    session = connect(bridged.control_port)
    try:
        buses = {one.identifier: one.kind.value for one in session.read_buses()}
    finally:
        session.close()

    assert buses[UART_BUS] == "uart"
    assert buses[CAN_BUS] == "can"
    assert CAN_BASE_ID > 0
