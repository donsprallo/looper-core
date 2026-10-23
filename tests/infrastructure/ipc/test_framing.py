"""Length prefixed framing over a real socket pair."""

from __future__ import annotations

import socket

import pytest

from looper.infrastructure.ipc.errors import SimulationUnreachableError
from looper.infrastructure.ipc.framing import MAXIMUM_FRAME_SIZE, receive_frame, send_frame


@pytest.fixture
def pair() -> tuple[socket.socket, socket.socket]:
    left, right = socket.socketpair()
    yield left, right
    left.close()
    right.close()


def test_a_frame_survives_the_round_trip(pair: tuple[socket.socket, socket.socket]) -> None:
    left, right = pair

    send_frame(left, b"\x08\x01\x10\x02")

    assert receive_frame(right) == b"\x08\x01\x10\x02"


def test_an_empty_frame_is_valid(pair: tuple[socket.socket, socket.socket]) -> None:
    left, right = pair

    send_frame(left, b"")

    assert receive_frame(right) == b""


def test_frames_keep_their_boundaries(pair: tuple[socket.socket, socket.socket]) -> None:
    left, right = pair

    send_frame(left, b"first")
    send_frame(left, b"second")

    assert receive_frame(right) == b"first"
    assert receive_frame(right) == b"second"


def test_an_oversized_frame_is_refused(pair: tuple[socket.socket, socket.socket]) -> None:
    left, _ = pair

    with pytest.raises(ValueError, match="exceeds"):
        send_frame(left, b"x" * (MAXIMUM_FRAME_SIZE + 1))


def test_a_closed_peer_is_reported(pair: tuple[socket.socket, socket.socket]) -> None:
    left, right = pair
    left.close()

    with pytest.raises(SimulationUnreachableError):
        receive_frame(right)
