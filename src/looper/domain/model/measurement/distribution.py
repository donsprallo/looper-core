"""How a measured time was spread, rather than what it averaged.

A mean and a worst case describe a distribution the way a first and
last name describe a person. The three shapes that matter in a
firmware all average the same and mean entirely different things:

- one hump, narrow: the call does one thing and always the same way
- two humps: two paths through it, and something chooses between them
- one hump with a long tail: it is usually fine and occasionally
  blocks, which is the one that breaks a deadline

None of the three can be told from the other two by any number. They
can be told apart at a glance from a picture of the spread, which is
what this is for.

Buckets are powers of two nanoseconds: bucket `n` holds everything
from 2^n up to 2^(n+1), and bucket zero holds the immeasurably
short. Chosen because a simulation measures times from nanoseconds
to seconds -- nine orders of magnitude -- and because a runtime can
find the bucket for a duration without dividing.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

NANOSECONDS_PER_SECOND = 1e9

#: Buckets kept. Thirty two powers of two reach from a nanosecond to
#: four seconds, and anything slower than that is not a detail.
BUCKET_COUNT = 32


def bucket_of(seconds: float) -> int:
    """Which bucket a duration belongs in.

    A duration below a nanosecond, and a clock that ran backwards,
    both land in the first band. The width of a band tells a reader
    what the number is worth, and the first one says "too short to
    measure" -- which is the truth about both.
    """
    nanoseconds = max(0, int(seconds * NANOSECONDS_PER_SECOND))
    return min(max(nanoseconds.bit_length() - 1, 0), BUCKET_COUNT - 1)


@dataclass(frozen=True)
class Bucket:
    """One band of durations and how many fell into it.

    Attributes:
        index: Which power of two the band begins at.
        count: How many measurements landed in it.
    """

    index: int
    count: int

    def __post_init__(self) -> None:
        if self.index < 0 or self.count < 0:
            raise ValueError("A bucket counts upwards from a positive band")

    @property
    def low_seconds(self) -> float:
        """The shortest duration this band holds."""
        return (2.0**self.index) / NANOSECONDS_PER_SECOND

    @property
    def high_seconds(self) -> float:
        """The first duration too long for this band."""
        return (2.0 ** (self.index + 1)) / NANOSECONDS_PER_SECOND


@dataclass(frozen=True)
class Distribution:
    """How many measurements fell into each band.

    Attributes:
        counts: One count per band, in order, the position being the
            power of two the band begins at.
    """

    counts: tuple[int, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if any(one < 0 for one in self.counts):
            raise ValueError("A band cannot hold a negative number of measurements")

    @property
    def total(self) -> int:
        """How many measurements there were altogether."""
        return sum(self.counts)

    @property
    def is_measured(self) -> bool:
        """Whether anything was measured at all."""
        return self.total > 0

    @property
    def buckets(self) -> tuple[Bucket, ...]:
        """Every band that holds something, shortest first."""
        return tuple(Bucket(index, count) for index, count in enumerate(self.counts) if count > 0)

    @property
    def busiest(self) -> Bucket | None:
        """The band most measurements landed in, or nothing."""
        return max(self.buckets, key=lambda one: one.count, default=None)

    @property
    def span(self) -> int:
        """How many bands apart the shortest and longest were.

        A rough measure of how spread out the thing is: one band
        means every call took about the same time, and ten means the
        slowest took a thousand times the fastest.
        """
        occupied = self.buckets
        return occupied[-1].index - occupied[0].index + 1 if occupied else 0

    @property
    def is_split(self) -> bool:
        """Whether the measurements fall into separated groups.

        An empty band between two occupied ones means the thing has
        two behaviours rather than one with variation. That is worth
        saying out loud: it is usually two paths through the code,
        and the question becomes which one is being taken when.
        """
        occupied = [one.index for one in self.buckets]
        return any(
            later - earlier > 1 for earlier, later in zip(occupied, occupied[1:], strict=False)
        )

    def at_most_seconds(self, fraction: float) -> float:
        """What this share of the measurements came in under.

        An upper bound rather than an interpolated estimate. The
        bands are wide and the honest answer to "where is the 95th
        percentile" is the end of the band it falls in -- which is
        also the number worth quoting, because it is the one nothing
        in that share exceeded.
        """
        if not self.is_measured:
            return 0.0
        wanted = max(1, round(self.total * fraction))
        seen = 0
        for one in self.buckets:
            seen += one.count
            if seen >= wanted:
                return one.high_seconds
        return self.buckets[-1].high_seconds


def distribute(values_seconds: Sequence[float]) -> Distribution:
    """Sort measurements into bands, for whatever was measured here.

    The runtime fills its own bands as it goes, because keeping every
    duration of eight thousand calls a second is not worth it. This
    is for the measurements a client already holds -- the gaps
    between recorded events, above all.
    """
    counts = [0] * BUCKET_COUNT
    for one in values_seconds:
        counts[bucket_of(one)] += 1
    return Distribution(tuple(counts))
