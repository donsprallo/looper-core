"""What a stream is asked before anything is drawn on it.

The three capabilities fail separately and in ways that are easy to
get wrong: a pipe takes colour codes it should never be given, and a
Windows console takes colour happily and then raises on a box drawing
character halfway through a build.
"""

from __future__ import annotations

import io

import pytest

from looper.presentation.cli.console import GREEN, Console, console_for
from looper.presentation.cli.progress_layout import DRAWN_CHARACTERS


class Terminal(io.TextIOWrapper):
    """A stream that claims to be one, in an encoding of its own."""

    def isatty(self) -> bool:
        return True


def a_terminal(encoding: str = "utf-8") -> Terminal:
    """A terminal that encodes the way the given console would."""
    return Terminal(io.BytesIO(), encoding=encoding)


def test_a_redirected_stream_is_given_nothing_at_all() -> None:
    console = console_for(io.StringIO(), DRAWN_CHARACTERS)

    assert not console.can_rewrite
    assert not console.can_colour
    assert not console.can_draw


def test_a_terminal_is_given_everything() -> None:
    console = console_for(a_terminal(), DRAWN_CHARACTERS)

    assert console.can_rewrite
    assert console.can_colour
    assert console.can_draw


def test_a_console_that_cannot_encode_the_symbols_is_not_sent_them() -> None:
    """Otherwise the display breaks the build it is reporting on."""
    console = console_for(a_terminal("cp1252"), DRAWN_CHARACTERS)

    assert console.can_rewrite
    assert not console.can_draw


def test_no_color_is_honoured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")

    console = console_for(a_terminal(), DRAWN_CHARACTERS)

    assert not console.can_colour
    assert console.can_rewrite


def test_a_dumb_terminal_is_treated_as_a_pipe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERM", "dumb")

    console = console_for(a_terminal(), DRAWN_CHARACTERS)

    assert not console.can_rewrite


def test_painting_is_left_out_where_colour_is_not_wanted() -> None:
    stream = io.StringIO()

    assert Console(stream=stream).paint("done", GREEN) == "done"
    assert Console(stream=stream, can_colour=True).paint("done", GREEN).startswith(GREEN)


def test_an_empty_string_is_never_painted() -> None:
    """A colour around nothing is two escape sequences and no text."""
    console = Console(stream=io.StringIO(), can_colour=True)

    assert console.paint("", GREEN) == ""
