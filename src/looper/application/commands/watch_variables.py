"""Use cases that start, stop and drive the watching of firmware variables."""

from __future__ import annotations

from looper.application.dto.variable_view import VariableView, WatchView, format_scalar
from looper.application.errors import VariableWriteRejectedError
from looper.application.mapping.variable_view import build_watch_view, to_firmware_variable
from looper.domain.ports import SimulationSession


class WatchVariable:
    """Starts sampling one firmware variable into the trace.

    The simulation reads the variable once per firmware loop iteration, which
    is why a watch shows what the firmware did rather than what happened to
    fall on a client poll.
    """

    def __init__(self, session: SimulationSession) -> None:
        self._session = session

    def execute(self, variable: VariableView) -> WatchView:
        """Watch a variable the caller picked out of the listing.

        Args:
            variable: Variable to read, as it was listed.

        Returns:
            The watch, carrying the trace channel the simulation allocated.

        Raises:
            ValueError: If the address is not readable or no channel is free.
        """
        watch = self._session.watch_variable(
            to_firmware_variable(variable), variable.runtime_address
        )
        return build_watch_view(watch)


class RemoveWatch:
    """Stops sampling a watched variable."""

    def __init__(self, session: SimulationSession) -> None:
        self._session = session

    def execute(self, channel_id: int) -> None:
        """Stop the watch on a trace channel.

        Raises:
            ValueError: If no watch holds that channel.
        """
        self._session.remove_variable_watch(channel_id)


class WriteVariable:
    """Writes a value into a watched firmware variable.

    What the write reaches is the firmware's own memory, so the firmware acts
    on it from the next loop iteration. That is the point of it, and also the
    reason the value is checked before it is sent: the simulation refuses the
    same writes, but only after a round trip and only in terms of a channel
    number.
    """

    def __init__(self, session: SimulationSession) -> None:
        self._session = session

    def execute(self, watch: WatchView, value: float) -> None:
        """Store a value in the variable a watch is reading.

        Args:
            watch: Watch naming the variable to write.
            value: Value to store, truncated towards zero for an integer.

        Raises:
            VariableWriteRejectedError: If the variable is read only or the
                value is outside the range it can hold.
            ValueError: If the simulation refuses the write for a reason the
                client could not see, such as the watch having been removed.
        """
        self._refuse_if_impossible(watch, value)
        self._session.write_variable(watch.channel_id, value)

    @staticmethod
    def _refuse_if_impossible(watch: WatchView, value: float) -> None:
        """Reject a write the variable cannot accept.

        Raises:
            VariableWriteRejectedError: If the write cannot succeed.
        """
        if not watch.is_writable:
            raise VariableWriteRejectedError(watch.path, "the variable is declared const")
        low, high = watch.value_range()
        if not low <= value <= high:
            raise VariableWriteRejectedError(
                watch.path,
                f"{format_scalar(value, watch.encoding)} is outside the range "
                f"{format_scalar(low, watch.encoding)} to {format_scalar(high, watch.encoding)}",
            )
