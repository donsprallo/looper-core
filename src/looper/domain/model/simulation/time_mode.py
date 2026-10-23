"""Selection between the two simulation time sources."""

from __future__ import annotations

from enum import Enum, unique


@unique
class TimeMode(Enum):
    """How simulated firmware time advances.

    ``VIRTUAL`` advances only when every firmware thread is blocked, which
    makes test runs deterministic and independent of host load. ``REAL_TIME``
    follows the host clock, which is what interactive inspection and the
    graphical interface require.
    """

    VIRTUAL = "virtual"
    REAL_TIME = "real_time"

    @property
    def supports_interactive_inspection(self) -> bool:
        """Whether a human driven client may observe this mode live."""
        return self is TimeMode.REAL_TIME
