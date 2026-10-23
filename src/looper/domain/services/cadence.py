"""How regularly something happened.

A mean tells you a frame went out every ten milliseconds. It does not
tell you that one of them went out after twenty-three, which is the
one that matters: a periodic thing that is late once is a thing whose
deadline is not being met, and no average will ever show it.

So the interesting number is not the period but the spread of the
periods, and the interesting picture is the period plotted against
time -- a flat line with one spike, rather than a column of figures
with the spike averaged into it.

Everything here is derived from moments a recording already carries.
Nothing has to be measured again.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from statistics import fmean, median

#: Two moments make one interval, so that is the least it takes to say
#: anything at all about how regular something is.
LEAST_MOMENTS = 2


def intervals_between(moments: Sequence[float]) -> tuple[float, ...]:
    """The gap between each pair of neighbouring moments.

    Args:
        moments: When something happened, oldest first.

    Returns:
        One gap fewer than there were moments, in the same order, so
        that the nth gap can be plotted against the nth moment.
    """
    return tuple(later - earlier for earlier, later in zip(moments, moments[1:], strict=False))


@dataclass(frozen=True)
class Cadence:
    """What the gaps between occurrences came to.

    Attributes:
        intervals: Every gap, in order, so that one of them can be
            found rather than only counted.
    """

    intervals: tuple[float, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if any(one < 0.0 for one in self.intervals):
            raise ValueError("Moments do not run backwards")

    @property
    def is_measured(self) -> bool:
        """Whether anything happened often enough to say."""
        return bool(self.intervals)

    @property
    def count(self) -> int:
        """How many gaps there were."""
        return len(self.intervals)

    @property
    def shortest_seconds(self) -> float:
        """The soonest it came round again."""
        return min(self.intervals, default=0.0)

    @property
    def longest_seconds(self) -> float:
        """The longest it stayed away, which is usually the finding."""
        return max(self.intervals, default=0.0)

    @property
    def mean_seconds(self) -> float:
        """The average gap."""
        return fmean(self.intervals) if self.intervals else 0.0

    @property
    def median_seconds(self) -> float:
        """The gap in the middle.

        Kept beside the mean because one late occurrence drags a mean
        and leaves a median alone, and the difference between the two
        is itself a reading: far apart means something went wrong
        rarely rather than everything being slightly off.
        """
        return median(self.intervals) if self.intervals else 0.0

    @property
    def jitter_seconds(self) -> float:
        """Longest gap less shortest, which is what jitter means here.

        Peak to peak rather than a deviation: a bus or a loop is
        judged by its worst case, and a standard deviation hides
        exactly the single excursion that breaks one.
        """
        return self.longest_seconds - self.shortest_seconds

    @property
    def frequency_hz(self) -> float:
        """How often it happened, taken from the median gap."""
        gap = self.median_seconds
        return 1.0 / gap if gap > 0.0 else 0.0

    def late_by(self, allowed_seconds: float) -> tuple[int, ...]:
        """Which gaps were longer than they were allowed to be.

        Args:
            allowed_seconds: The longest acceptable gap.

        Returns:
            The positions of the gaps that exceeded it, so that a
            reader can be taken to the moment rather than told a
            count.
        """
        return tuple(
            position for position, one in enumerate(self.intervals) if one > allowed_seconds
        )


def cadence_of(moments: Sequence[float]) -> Cadence:
    """How regularly a thing recurred.

    Args:
        moments: When it happened, oldest first.

    Returns:
        Its cadence, which reports nothing when there were fewer than
        two moments -- one occurrence has no period, and inventing one
        would be the first lie in a chain of them.
    """
    if len(moments) < LEAST_MOMENTS:
        return Cadence()
    return Cadence(intervals_between(moments))
