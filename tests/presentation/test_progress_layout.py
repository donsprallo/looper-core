"""How one step of a command is written on one line.

The layout is pure text, so this is where the look is pinned down:
what a duration reads like, how much of the bar is filled, and that
nothing a console cannot do is written to it.
"""

from __future__ import annotations

import io

import pytest

from looper.presentation.cli.console import Console
from looper.presentation.cli.progress_layout import (
    BAR_WIDTH,
    DRAWN,
    PLAIN,
    LiveStep,
    bar,
    elapsed_text,
    failed_line,
    finished_line,
    running_line,
    symbols_for,
)


def a_console(**capabilities: bool) -> Console:
    """A console over a string, told what it is allowed to do."""
    return Console(stream=io.StringIO(), **capabilities)


@pytest.mark.parametrize(
    ("seconds", "text"),
    [
        (0.0, "0.00 s"),
        (0.004, "0.00 s"),
        (1.237, "1.24 s"),
        (12.34, "12.3 s"),
        (59.9, "59.9 s"),
        (60.0, "1 m 00 s"),
        (131.4, "2 m 11 s"),
    ],
)
def test_a_duration_reads_the_way_a_person_would_say_it(seconds: float, text: str) -> None:
    assert elapsed_text(seconds) == text


def test_the_bar_fills_with_the_steps_that_are_done() -> None:
    assert bar(0, 6, 12) == (0, 12)
    assert bar(3, 6, 12) == (6, 6)
    assert bar(6, 6, 12) == (12, 0)


def test_the_bar_never_overflows_its_width() -> None:
    """A use case may announce more steps than it said it would."""
    assert bar(9, 6, 12) == (12, 0)
    assert bar(-1, 6, 12) == (0, 12)


def test_a_bar_without_steps_to_count_stays_empty() -> None:
    assert bar(1, 0, 12) == (0, 12)


def test_a_plain_console_is_given_no_colour_and_no_drawings() -> None:
    console = a_console()
    line = finished_line(console, symbols_for(console.can_draw), "Compiling", 1.5, "blinky.exe")

    assert line == "  + Compiling                        1.50 s  blinky.exe"
    assert "\x1b" not in line


def test_a_capable_console_is_given_both() -> None:
    console = a_console(can_colour=True, can_draw=True)

    line = finished_line(console, DRAWN, "Compiling", 1.5, "blinky.exe")

    assert DRAWN.done in line
    assert "\x1b[32m" in line


def test_a_step_that_failed_says_so_rather_than_showing_a_time_alone() -> None:
    console = a_console()

    line = failed_line(console, PLAIN, "Compiling and linking", 8.0)

    assert line.startswith(f"  {PLAIN.failed} Compiling and linking")
    assert line.endswith("failed")


def test_a_finished_step_without_a_summary_leaves_no_trailing_space() -> None:
    console = a_console()

    line = finished_line(console, PLAIN, "Writing the sources", 0.1, "")

    assert line == line.rstrip()


def a_step(**overrides: object) -> LiveStep:
    """The sixth step of six, running."""
    values: dict[str, object] = {
        "activity": "Compiling",
        "position": 6,
        "count": 6,
        "seconds": 1.0,
    }
    values.update(overrides)
    return LiveStep(**values)  # type: ignore[arg-type]


def test_the_running_line_counts_the_step_it_is_drawing_as_unfinished() -> None:
    """A full bar above work still going on would be a lie."""
    console = a_console()

    line = running_line(console, PLAIN, 0, a_step())

    assert line.count(PLAIN.filled) == BAR_WIDTH - BAR_WIDTH // 6
    assert "6/6" in line


def test_a_step_that_reports_its_own_progress_moves_the_bar_through_itself() -> None:
    """Otherwise the bar stands still through the one slow step."""
    console = a_console()

    half = running_line(console, PLAIN, 0, a_step(done=70, total=140))
    nearly = running_line(console, PLAIN, 0, a_step(done=139, total=140))

    assert half.count(PLAIN.filled) == 11
    assert nearly.count(PLAIN.filled) == BAR_WIDTH
    assert "70/140" in half


def test_what_a_step_is_working_on_is_named_last_of_all() -> None:
    """The only thing that changes length sits where nothing follows it."""
    console = a_console()

    line = running_line(console, PLAIN, 0, a_step(done=37, total=140, detail="app_config.c"))

    assert line.endswith("app_config.c")
    assert line.index("37/140") < line.index("1.00 s") < line.index("app_config.c")


def test_the_count_of_parts_is_padded_to_its_own_total() -> None:
    """So that the time beside it does not step sideways 143 times."""
    console = a_console()

    first = running_line(console, PLAIN, 0, a_step(done=7, total=143, detail="a.c"))
    last = running_line(console, PLAIN, 0, a_step(done=143, total=143, detail="a.c"))

    assert "  7/143" in first
    assert first.index("1.00 s") == last.index("1.00 s")


def test_a_step_that_says_nothing_about_itself_shows_no_fraction() -> None:
    console = a_console()

    line = running_line(console, PLAIN, 0, a_step(position=1))

    assert "/6" in line
    assert "0/0" not in line


def test_the_spinner_turns_with_the_frame() -> None:
    console = a_console()
    drawn = [
        running_line(console, PLAIN, frame, a_step(position=1, count=2))[2] for frame in range(5)
    ]

    assert drawn[: len(PLAIN.spinner)] == list(PLAIN.spinner)
    assert drawn[len(PLAIN.spinner)] == PLAIN.spinner[0]
