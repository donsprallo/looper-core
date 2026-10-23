"""Reducing a trace to as many points as are worth keeping.

A firmware samples faster than anything shows it. A converter at eight
kilohertz fills a five second window with forty thousand points, and a plot
a thousand pixels wide can show one column per pixel: carrying all of them
spends almost all of its time on points that land on top of each other.

Throwing most of them away would be wrong, though. A scope that showed
every thousandth sample would miss the spike between them, and a spike is
usually the thing being looked for. So each column keeps the lowest and the
highest value that fell in it, which draws the same envelope the full trace
would draw, out of two points per column instead of forty.

Here rather than beside the drawing because two layers want it. A plot
reduces to the pixels it has; a reading reduces to what is worth handing
over at all, before several thousand points are made into objects nobody
can see apart.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

#: Columns are pixels, and there is no point in more than one point per
#: half pixel; below this the trace is drawn as it is.
MINIMUM_COLUMNS = 2


def decimate(
    points: Sequence[tuple[float, float]],
    start_seconds: float,
    span_seconds: float,
    columns: int,
) -> list[tuple[float, float]]:
    """Reduce a trace to at most two points per column.

    Args:
        points: Time and value pairs, oldest first.
        start_seconds: Time the visible window begins at.
        span_seconds: Length of the visible window.
        columns: Number of columns the window is drawn across.

    Returns:
        The points to draw, oldest first. Fewer points than columns are
        returned unchanged, because there is nothing to gain.
    """
    if (columns < MINIMUM_COLUMNS) or (span_seconds <= 0.0):
        return list(points)
    if len(points) <= (columns * 2):
        return list(points)
    return _envelope(points, start_seconds, span_seconds, columns)


def _envelope(
    points: Sequence[tuple[float, float]],
    start_seconds: float,
    span_seconds: float,
    columns: int,
) -> list[tuple[float, float]]:
    """Keep the lowest and highest value of each column, in time order.

    The hot loop of the whole plot: it runs once per channel per repaint
    over every point in the window, so the scale is worked out once and the
    comparisons are on bare floats rather than on tuples.
    """
    reduced: list[tuple[float, float]] = []
    scale = columns / span_seconds
    current = -1
    low = high = low_time = high_time = 0.0

    for seconds, value in points:
        column = int((seconds - start_seconds) * scale)
        if column != current:
            _append(reduced, (low_time, low), (high_time, high), current)
            current, low, high, low_time, high_time = column, value, value, seconds, seconds
        elif value < low:
            low, low_time = value, seconds
        elif value > high:
            high, high_time = value, seconds
    _append(reduced, (low_time, low), (high_time, high), current)
    return reduced


def _append(
    reduced: list[tuple[float, float]],
    lowest: tuple[float, float],
    highest: tuple[float, float],
    column: int,
) -> None:
    """Add one column's two points, in the order they were sampled."""
    if column < 0:
        return
    if lowest == highest:
        reduced.append(lowest)
        return
    first, second = (lowest, highest) if lowest[0] <= highest[0] else (highest, lowest)
    reduced.append(first)
    reduced.append(second)


def value_range(points: Iterable[tuple[float, float]]) -> tuple[float, float] | None:
    """Lowest and highest value in one pass, or ``None`` when there are none."""
    lowest: float | None = None
    highest: float | None = None

    for _, value in points:
        if (lowest is None) or (value < lowest):
            lowest = value
        if (highest is None) or (value > highest):
            highest = value
    if (lowest is None) or (highest is None):
        return None
    return lowest, highest
