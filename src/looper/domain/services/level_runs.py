"""The stretches a pin spent at one level.

A logic analyser does not draw moments, it draws bands: high from
here to there, low from there to the next change. Turning a list of
changes into those bands is a small piece of arithmetic with two
awkward ends, and both of them decide whether the picture is honest.

The last run has no change to end it. It runs to the end of what is
being shown, because that is what the recording says -- the pin is
still at that level -- and drawing it to the last change instead
would show a signal that stopped.

The first run has no change to begin it. Before the earliest change
nothing is known, and nothing is what is drawn: a pin registered
after the window opened did not spend that time low, it spent it
unobserved.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import islice

from looper.domain.model.simulation import PinChange, SignalLevel


@dataclass(frozen=True)
class LevelRun:
    """A stretch during which a pin stayed where it was.

    Attributes:
        level: The level it held.
        start_seconds: When it took that level.
        end_seconds: When it left it, or the end of what is shown.
        is_open: Whether it is still at this level, so far as the
            recording says, rather than having been seen to leave it.
    """

    level: SignalLevel
    start_seconds: float
    end_seconds: float
    is_open: bool = False

    def __post_init__(self) -> None:
        if self.end_seconds < self.start_seconds:
            raise ValueError("A run ends no earlier than it begins")

    @property
    def duration_seconds(self) -> float:
        """How long it lasted."""
        return self.end_seconds - self.start_seconds

    @property
    def is_high(self) -> bool:
        """Whether this is a high stretch rather than a low one."""
        return self.level is SignalLevel.HIGH


def runs_of(changes: Sequence[PinChange], until_seconds: float) -> tuple[LevelRun, ...]:
    """Turn a pin's changes into the stretches between them.

    Args:
        changes: What the pin did, oldest first.
        until_seconds: The end of what is being shown, which is where
            the last run reaches.

    Returns:
        One run per change. Nothing at all when the pin never
        changed, because a pin with no recorded level is a pin
        nothing is known about rather than a pin that was low.
    """
    if not changes:
        return ()
    after_the_first = islice(changes, 1, None)
    ends = [*(one.seconds for one in after_the_first), max(until_seconds, changes[-1].seconds)]
    return tuple(
        LevelRun(
            level=change.level,
            start_seconds=change.seconds,
            end_seconds=end,
            is_open=position == len(changes) - 1,
        )
        for position, (change, end) in enumerate(zip(changes, ends, strict=True))
    )
