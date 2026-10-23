"""One request out, one response back, over a socket.

Separated from the session because the two answer different questions. This
one is about the wire: numbering requests, framing them, and refusing an
answer that does not belong to the question. The session is about what the
simulation can be asked.
"""

from __future__ import annotations

import logging
import socket
from typing import cast

from looper.domain.ports import SimulationRejectedError
from looper.infrastructure.ipc.errors import SimulationUnreachableError
from looper.infrastructure.ipc.framing import receive_frame, send_frame
from looper.infrastructure.ipc.generated import looper_control_pb2 as protocol

logger = logging.getLogger(__name__)

STALE_ANSWER_LIMIT = 64
"""How many answers to an abandoned request may be skipped.

A guard, not a tuning knob: beyond this the socket is not merely one
answer behind, and reading on would hang instead of failing."""


class RequestExchange:
    """Sends requests over one connection and matches up the answers.

    Requests are numbered so that a response can be checked against the
    request it claims to answer. A mismatch means the stream is out of step,
    which is not something to recover from silently.
    """

    def __init__(self, connection: socket.socket) -> None:
        self._connection = connection
        self._next_request_id = 1

    def close(self) -> None:
        """Release the connection. Closing an already closed one is allowed."""
        self._connection.close()

    def send(
        self,
        command: int,
        *,
        pin: int = 0,
        level: int = 0,
        microseconds: int = 0,
        channel: int = 0,
        signal: protocol.Signal | None = None,
        after_sequence: int = 0,
        address: int = 0,
        encoding: int = 0,
        byte_width: int = 0,
        bit_offset: int = 0,
        bit_width: int = 0,
        path: str = "",
        writable: bool = False,
        value: float = 0.0,
        bus: int = 0,
        bus_address: protocol.BusAddress | None = None,
        payload: bytes = b"",
        label: str = "",
        watching: bool = False,
    ) -> protocol.Response:
        """Send one request and return the response that answers it.

        The protobuf stubs type enum fields as their wrapper class while the
        runtime accepts plain integers, so the enum arguments are cast.

        Raises:
            SimulationRejectedError: If the simulation reports a failure.
            SimulationUnreachableError: If the answer does not match the request.
        """
        request = protocol.Request(
            id=self._next_request_id,
            command=cast(protocol.Command, command),
            pin=pin,
            level=cast(protocol.SignalLevel, level),
            microseconds=microseconds,
            channel=channel,
            signal=signal,
            after_sequence=after_sequence,
            address=address,
            encoding=cast(protocol.VariableEncoding, encoding),
            byte_width=byte_width,
            bit_offset=bit_offset,
            bit_width=bit_width,
            path=path,
            writable=writable,
            value=value,
            bus=bus,
            bus_address=bus_address,
            payload=payload,
            label=label,
            watching=watching,
        )
        self._next_request_id += 1
        return self._answer(request)

    def _answer(self, request: protocol.Request) -> protocol.Response:
        """Write the request, read the response, and check the two match.

        An answer to an **older** request is dropped and the next one read.
        One request that was given up on - a timeout, a caller interrupted
        between writing and reading - otherwise leaves its answer in the
        socket, and from then on every response belongs to the request
        before: the session reports "expected 600087, got 600086" and keeps
        reporting it, one off, until the process ends. Measured on
        2026-10-18 against a large firmware simulation, where it took a
        whole test plan down after the first timeout.

        Skipping is safe because ids only grow: an id below the one asked
        for cannot belong to a question that is still open.

        Raises:
            SimulationRejectedError: If the simulation reports a failure.
            SimulationUnreachableError: If the answer does not match the
                request, or if the answers run ahead of it.
        """
        send_frame(self._connection, request.SerializeToString())
        response = protocol.Response()
        response.ParseFromString(receive_frame(self._connection))

        dropped = 0
        while response.id < request.id:
            dropped += 1
            if dropped > STALE_ANSWER_LIMIT:
                raise SimulationUnreachableError(
                    f"More than {STALE_ANSWER_LIMIT} stale answers before "
                    f"request {request.id}; the session is out of step"
                )
            response = protocol.Response()
            response.ParseFromString(receive_frame(self._connection))
        if dropped:
            logger.debug("dropped %d stale answer(s) before request %d", dropped, request.id)

        if response.id != request.id:
            raise SimulationUnreachableError(
                f"Expected an answer to request {request.id}, got {response.id}"
            )
        if response.status != protocol.STATUS_OK:
            raise SimulationRejectedError(response.message or "the simulation refused the request")
        return response
