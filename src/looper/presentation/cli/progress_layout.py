"""How one step of a command is written on one line.

Pure text, so that what a progress display looks like can be read and
tested without a terminal, a thread or a clock. What varies is kept to
two things: the symbols, because not every console has them, and the
console's willingness to take colour.
"""

from __future__ import annotations

from dataclasses import dataclass

from looper.presentation.cli.console import CYAN, DIM, GREEN, RED, Console

#: Columns the activity is given, so that the times line up under each
#: other. The longest step name is a little shorter than this.
ACTIVITY_WIDTH = 30

#: Columns the elapsed time is right aligned in.
TIME_WIDTH = 8

#: Cells in the bar. Twelve is enough to see a sixth of the work go by
#: and narrow enough to leave room for the step name on 80 columns.
BAR_WIDTH = 12

SECONDS_PER_MINUTE = 60.0

#: Below this, hundredths say something; above it they are noise.
FINE_SECONDS = 10.0


@dataclass(frozen=True)
class Symbols:
    """The characters a progress display is drawn with.

    Attributes:
        spinner: Frames shown in turn while a step is running.
        done: Marks a step that finished.
        failed: Marks a step that did not.
        filled: One completed cell of the bar.
        empty: One cell still to come.
    """

    spinner: tuple[str, ...]
    done: str
    failed: str
    filled: str
    empty: str


#: What a console with a modern font draws.
DRAWN = Symbols(
    spinner=("\u280b", "\u2819", "\u2839", "\u2838", "\u283c", "\u2834", "\u2826", "\u2827"),
    done="\u2714",
    failed="\u2716",
    filled="\u2588",
    empty="\u2591",
)

#: What everything else draws. Same widths, so the layout does not move.
PLAIN = Symbols(spinner=("|", "/", "-", "\\"), done="+", failed="x", filled="#", empty=".")

#: Every character the drawn set needs, for asking a stream whether it
#: can encode them before anything is written.
DRAWN_CHARACTERS = "".join((*DRAWN.spinner, DRAWN.done, DRAWN.failed, DRAWN.filled, DRAWN.empty))


def symbols_for(can_draw: bool) -> Symbols:
    """The set this console can show."""
    return DRAWN if can_draw else PLAIN


def elapsed_text(seconds: float) -> str:
    """How long something took, as a person would say it."""
    if seconds < FINE_SECONDS:
        return f"{seconds:.2f} s"
    if seconds < SECONDS_PER_MINUTE:
        return f"{seconds:.1f} s"
    minutes, rest = divmod(int(seconds), int(SECONDS_PER_MINUTE))
    return f"{minutes} m {rest:02d} s"


def bar(completed: float, count: int, width: int = BAR_WIDTH) -> tuple[int, int]:
    """How many cells of the bar are done and how many are not.

    Steps completed may be fractional, because a step that reports its
    own progress is partly done, and a bar that sits still through the
    one step that takes all the time is the bar nobody wanted.
    """
    if count <= 0:
        return 0, width
    filled = min(width, max(0, round(width * completed / count)))
    return filled, width - filled


def finished_line(
    console: Console, symbols: Symbols, activity: str, seconds: float, summary: str
) -> str:
    """The line a completed step leaves behind."""
    return _closed_line(console, symbols.done, GREEN, activity, seconds, summary)


def failed_line(console: Console, symbols: Symbols, activity: str, seconds: float) -> str:
    """The line a step that raised leaves behind."""
    return _closed_line(console, symbols.failed, RED, activity, seconds, "failed")


def _closed_line(
    console: Console, mark: str, colour: str, activity: str, seconds: float, summary: str
) -> str:
    """One step, over with, one way or the other."""
    elapsed = elapsed_text(seconds).rjust(TIME_WIDTH)
    return (
        f"  {console.paint(mark, colour)} {activity:<{ACTIVITY_WIDTH}}"
        f" {console.paint(elapsed, DIM)}  {console.paint(summary, DIM)}"
    ).rstrip()


@dataclass(frozen=True)
class LiveStep:
    """The step a running display is drawing.

    Attributes:
        activity: What is being done.
        position: Which step of the plan it is, counting from one.
        count: How many steps the plan has.
        seconds: How long this one has been running.
        done: Parts of this step that are finished, for a step that
            reports its own progress.
        total: Parts there are. Zero when the step does not say.
        detail: What the step is on right now.
    """

    activity: str
    position: int
    count: int
    seconds: float
    done: int = 0
    total: int = 0
    detail: str = ""

    @property
    def completed_steps(self) -> float:
        """How much of the plan is behind this display.

        The step being drawn is still running, so it counts only as
        far as it says it has got. A full bar above work in progress
        would be the display lying about the one thing it is for.
        """
        if self.total <= 0:
            return self.position - 1
        return self.position - 1 + min(1.0, self.done / self.total)


def running_line(console: Console, symbols: Symbols, frame: int, step: LiveStep) -> str:
    """The line a step shows while it is still working.

    Everything that changes length is at the end. The count of parts
    is padded to the width of its own total and the elapsed time to
    the width of the longest it will be, so the only thing that moves
    from one frame to the next is the name of the file -- which is
    the one thing nothing is lined up against.
    """
    columns = [f"  {_turning(console, symbols, frame)} {_bar(console, symbols, step)}"]
    columns.append(console.paint(f"{step.position}/{step.count}", DIM))
    columns.append(step.activity)
    columns.extend(console.paint(one, DIM) for one in _measurements(step))
    columns.append(console.paint(step.detail, DIM))
    return "  ".join(one for one in columns if one).rstrip()


def _measurements(step: LiveStep) -> tuple[str, ...]:
    """How far through itself the step is, and how long it has taken."""
    elapsed = elapsed_text(step.seconds).rjust(TIME_WIDTH)
    if step.total <= 0:
        return (elapsed,)
    return (f"{step.done:>{len(str(step.total))}}/{step.total}", elapsed)


def _turning(console: Console, symbols: Symbols, frame: int) -> str:
    """The frame of the spinner that is showing."""
    return console.paint(symbols.spinner[frame % len(symbols.spinner)], CYAN)


def _bar(console: Console, symbols: Symbols, step: LiveStep) -> str:
    """The bar, as far as the plan has got."""
    filled, empty = bar(step.completed_steps, step.count)
    return console.paint(symbols.filled * filled, CYAN) + console.paint(symbols.empty * empty, DIM)
