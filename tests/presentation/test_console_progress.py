"""What the progress display puts on the screen, and what it does not.

The display is driven by a use case it cannot see, so what is checked
here is the state machine around that: one line per step, a step that
raises closed as a failure rather than a success, and a console that
cannot rewrite lines never asked to.
"""

from __future__ import annotations

import io

import pytest

from looper.domain.ports import SilentProgress
from looper.presentation.cli.console import ERASE_LINE, Console
from looper.presentation.cli.progress import ConsoleProgress, report_progress

STEPS = ("Reading", "Compiling")


def a_display(**capabilities: bool) -> tuple[ConsoleProgress, io.StringIO]:
    """A display over a string, told what its console can do."""
    stream = io.StringIO()
    return ConsoleProgress(Console(stream=stream, **capabilities), len(STEPS)), stream


def test_each_finished_step_leaves_exactly_one_line() -> None:
    progress, stream = a_display()

    for step in STEPS:
        progress.begin(step)
        progress.end("done")

    written = [line for line in stream.getvalue().splitlines() if line]
    assert len(written) == len(STEPS)
    assert written[0].startswith("  + Reading")


def test_a_console_that_cannot_rewrite_is_not_given_a_live_line() -> None:
    """A log file of half-drawn steps is not a log file anybody wants."""
    progress, stream = a_display()

    progress.begin("Reading")
    progress.tick()
    progress.tick()

    assert stream.getvalue() == ""


def test_a_console_that_can_rewrite_redraws_in_place() -> None:
    progress, stream = a_display(can_rewrite=True)

    progress.begin("Reading")
    progress.tick()

    written = stream.getvalue()
    assert written.count(ERASE_LINE) == 2
    assert "\n" not in written


def test_a_step_that_reports_its_parts_redraws_at_once() -> None:
    """A unit that compiles in fifty milliseconds is never seen otherwise."""
    progress, stream = a_display(can_rewrite=True)

    progress.begin("Compiling and linking")
    progress.advance(37, 140, "app_config.c")

    written = stream.getvalue()
    assert "37/140" in written
    assert written.endswith("app_config.c")


def test_what_one_step_reported_is_not_carried_into_the_next() -> None:
    progress, stream = a_display(can_rewrite=True)
    progress.begin("Compiling")
    progress.advance(37, 140, "app_config.c")
    progress.end("done")

    progress.begin("Reading")

    assert "app_config.c" not in stream.getvalue().rsplit(ERASE_LINE, 1)[-1]


def test_reporting_parts_with_no_step_running_draws_nothing() -> None:
    progress, stream = a_display(can_rewrite=True)

    progress.advance(1, 10, "app.c")

    assert stream.getvalue() == ""


def test_a_step_that_is_abandoned_is_reported_as_failed() -> None:
    progress, stream = a_display()

    progress.begin("Compiling")
    progress.abandon()

    assert stream.getvalue().rstrip().endswith("failed")


def test_abandoning_with_nothing_open_writes_nothing() -> None:
    progress, stream = a_display()

    progress.begin("Reading")
    progress.end("8 functions")
    progress.abandon()

    assert "failed" not in stream.getvalue()


def test_the_display_parts_itself_from_what_the_command_prints_next() -> None:
    """The blank line comes as soon as the last planned step is done.

    ``run`` hands the terminal to a simulation immediately afterwards,
    and waiting for the context to close would mean waiting for that.
    """
    progress, stream = a_display()

    for step in STEPS:
        progress.begin(step)
        progress.end("")

    assert stream.getvalue().endswith("\n\n")


def test_closing_adds_nothing_once_the_display_has_parted() -> None:
    progress, stream = a_display()
    for step in STEPS:
        progress.begin(step)
        progress.end("")

    progress.close()

    assert stream.getvalue().endswith("\n\n")


def test_more_steps_than_planned_grow_the_count_rather_than_overflow_it() -> None:
    progress, stream = a_display(can_rewrite=True)

    for step in ("one", "two", "three"):
        progress.begin(step)
        progress.end("")

    assert "3/3" in stream.getvalue()


def test_being_quiet_hands_out_a_listener_that_says_nothing() -> None:
    with report_progress("build", STEPS, quiet=True) as progress:
        assert isinstance(progress, SilentProgress)


def test_a_step_still_open_when_the_command_raises_is_closed_as_a_failure(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with (
        pytest.raises(ValueError, match="the compiler said no"),
        report_progress("build  looper.toml", STEPS) as progress,
    ):
        progress.begin("Compiling")
        raise ValueError("the compiler said no")

    assert "failed" in capsys.readouterr().err
