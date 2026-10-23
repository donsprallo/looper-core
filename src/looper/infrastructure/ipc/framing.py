"""Length prefixed framing of control protocol messages."""

from __future__ import annotations

import socket
from typing import Literal

from looper.infrastructure.ipc.errors import SimulationUnreachableError

HEADER_SIZE = 4
BYTE_ORDER: Literal["little"] = "little"
MAXIMUM_FRAME_SIZE = 32768


def send_frame(connection: socket.socket, payload: bytes) -> None:
    """Send one length prefixed frame.

    Raises:
        SimulationUnreachableError: If the connection broke while sending.
        ValueError: If the payload exceeds the agreed frame size.
    """
    if len(payload) > MAXIMUM_FRAME_SIZE:
        raise ValueError(f"A frame of {len(payload)} bytes exceeds {MAXIMUM_FRAME_SIZE}")
    header = len(payload).to_bytes(HEADER_SIZE, BYTE_ORDER)
    try:
        connection.sendall(header + payload)
    except OSError as error:
        raise SimulationUnreachableError(f"Sending failed: {error}") from error


def receive_frame(connection: socket.socket) -> bytes:
    """Receive one length prefixed frame.

    Raises:
        SimulationUnreachableError: If the connection broke or the frame is
            larger than the agreed frame size.
    """
    length = int.from_bytes(_receive_exactly(connection, HEADER_SIZE), BYTE_ORDER)
    if length > MAXIMUM_FRAME_SIZE:
        raise SimulationUnreachableError(f"The simulation announced {length} bytes")
    return _receive_exactly(connection, length)


def _receive_exactly(connection: socket.socket, count: int) -> bytes:
    """Read exactly the requested number of bytes."""
    chunks: list[bytes] = []
    remaining = count
    while remaining > 0:
        try:
            chunk = connection.recv(remaining)
        except OSError as error:
            raise SimulationUnreachableError(f"Receiving failed: {error}") from error
        if not chunk:
            raise SimulationUnreachableError("The simulation closed the connection")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)
