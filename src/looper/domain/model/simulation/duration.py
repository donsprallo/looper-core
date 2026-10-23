"""How a duration is written where a person reads it.

Nanoseconds are the unit everything is measured in and none of it is
shown in. A call that takes 83 ns and a loop that takes 457 ms belong in
the same column, so the unit follows the number rather than the other
way round.
"""

from __future__ import annotations

NANOSECONDS_PER_MICROSECOND = 1_000
NANOSECONDS_PER_MILLISECOND = 1_000_000
NANOSECONDS_PER_SECOND = 1_000_000_000


def duration_text(nanoseconds: float) -> str:
    """A duration in the unit that makes it readable."""
    if nanoseconds < NANOSECONDS_PER_MICROSECOND:
        return f"{nanoseconds:.0f} ns"
    if nanoseconds < NANOSECONDS_PER_MILLISECOND:
        return f"{nanoseconds / NANOSECONDS_PER_MICROSECOND:.1f} us"
    if nanoseconds < NANOSECONDS_PER_SECOND:
        return f"{nanoseconds / NANOSECONDS_PER_MILLISECOND:.2f} ms"
    return f"{nanoseconds / NANOSECONDS_PER_SECOND:.2f} s"
