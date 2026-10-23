"""The progress display of the command line.

One line is live at a time. It carries a spinner so that a long step
visibly is not a hang, a bar so that six steps feel like six, and the
time the step has been running. When the step finishes the same line
is replaced by what it came to -- a mark, the name, how long it took
and what it produced -- and the next step takes over below it.

Everything goes to standard error. A build's report belongs on
standard output where a script can read it, and a script reading a
report should not have to filter a spinner out of it.
"""

from __future__ import annotations

import sys
import threading
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager

from looper.domain.ports import ProgressListener, SilentProgress
from looper.presentation.cli.animation import Animation
from looper.presentation.cli.console import BOLD, Console, console_for
from looper.presentation.cli.progress_layout import (
    DRAWN_CHARACTERS,
    LiveStep,
    Symbols,
    failed_line,
    finished_line,
    running_line,
    symbols_for,
)


class ConsoleProgress(ProgressListener):
    """Draws what a use case announces, one line per step.

    The animation calls `tick` from its own thread while the main
    thread is inside a step, so every piece of state here is held
    under one lock. There is little of it and it is held briefly.
    """

    def __init__(self, console: Console, step_count: int) -> None:
        self._console = console
        self._symbols: Symbols = symbols_for(console.can_draw)
        self._planned = step_count
        self._position = 0
        self._activity = ""
        self._started = 0.0
        self._frame = 0
        self._within = (0, 0, "")
        self._separated = False
        self._lock = threading.Lock()

    def begin(self, activity: str) -> None:
        """Start drawing a step."""
        with self._lock:
            self._position += 1
            self._activity = activity
            self._started = time.monotonic()
            self._frame = 0
            self._within = (0, 0, "")
            self._draw()

    def end(self, summary: str = "") -> None:
        """Replace the live line with what the step came to."""
        with self._lock:
            if not self._activity:
                return
            self._console.line(
                finished_line(
                    self._console, self._symbols, self._activity, self._elapsed(), summary
                )
            )
            self._activity = ""
            self._separate_after_last_step()

    def abandon(self) -> None:
        """Close a step that never finished, as the failure it was."""
        with self._lock:
            if not self._activity:
                return
            self._console.line(
                failed_line(self._console, self._symbols, self._activity, self._elapsed())
            )
            self._activity = ""

    def advance(self, done: int, total: int, detail: str = "") -> None:
        """Redraw the live line with how far through itself the step is.

        Straight away rather than at the next frame, because a unit
        that compiles in fifty milliseconds would otherwise never be
        seen, and the name going past is half of what makes a long
        step readable.
        """
        with self._lock:
            if not self._activity:
                return
            self._within = (done, total, detail)
            self._draw()

    def tick(self) -> None:
        """Draw the next frame, if a step is running at all."""
        with self._lock:
            if not self._activity:
                return
            self._frame += 1
            self._draw()

    def close(self) -> None:
        """Take back anything unfinished and leave one blank line."""
        with self._lock:
            self._console.clear()
            self._separate()

    def _draw(self) -> None:
        """Paint the live line."""
        done, total, detail = self._within
        step = LiveStep(
            activity=self._activity,
            position=self._position,
            count=self._total(),
            seconds=self._elapsed(),
            done=done,
            total=total,
            detail=detail,
        )
        self._console.transient(running_line(self._console, self._symbols, self._frame, step))

    def _separate_after_last_step(self) -> None:
        """Part the display from whatever the command prints next.

        As soon as the last planned step is done, because what comes
        next may be a simulation that holds the terminal for an hour.
        """
        if self._position >= self._planned:
            self._separate()

    def _separate(self) -> None:
        """Write the one blank line that follows the display."""
        if self._separated:
            return
        self._console.line("")
        self._separated = True

    def _total(self) -> int:
        """How many steps there will be, as far as is known.

        The plan is what the caller was told to expect. A use case
        that announces more than that is believed rather than
        squeezed into a bar that is already full.
        """
        return max(self._planned, self._position)

    def _elapsed(self) -> float:
        """How long the running step has taken so far."""
        return time.monotonic() - self._started


@contextmanager
def report_progress(
    title: str, steps: Sequence[str], quiet: bool = False
) -> Iterator[ProgressListener]:
    """Show what a command is doing for as long as it is doing it.

    Args:
        title: What the command is, written above the steps.
        steps: What it will announce, so the bar knows how far along
            each one is.
        quiet: Draw nothing at all.
    """
    if quiet:
        yield SilentProgress()
        return
    console = console_for(sys.stderr, DRAWN_CHARACTERS)
    progress = ConsoleProgress(console, len(steps))
    console.line(console.paint(title, BOLD))
    animation = _animation_for(console, progress)
    try:
        yield progress
    except BaseException:
        progress.abandon()
        raise
    finally:
        if animation is not None:
            animation.stop()
        progress.close()


def _animation_for(console: Console, progress: ConsoleProgress) -> Animation | None:
    """A turning spinner where one can be drawn, and nothing elsewhere."""
    if not console.can_rewrite:
        return None
    animation = Animation(progress.tick)
    animation.start()
    return animation
