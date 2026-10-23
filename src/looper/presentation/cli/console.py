"""What the terminal a command is writing to can actually do.

Three capabilities, asked once and carried around as answers rather
than re-derived at every write: whether a line can be drawn over
again, whether colour means anything, and whether the font has the
symbols. They are separate because they fail separately -- a pipe can
take colour codes it should not be given, a Windows console takes
colour happily and chokes on a box drawing character -- and because a
progress display that guesses wrong is worse than none at all.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TextIO

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
RED = "\x1b[31m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
CYAN = "\x1b[36m"

#: Back to the start of the line and wipe what was there.
ERASE_LINE = "\r\x1b[K"

#: A terminal that says it is this cannot do any of it.
DUMB_TERMINAL = "dumb"


@dataclass(frozen=True)
class Console:
    """One output stream and what it is capable of.

    Attributes:
        stream: Where the text goes.
        can_rewrite: Whether a line can be replaced by the next one,
            which is what makes a live display possible.
        can_colour: Whether ANSI colour is wanted here.
        can_draw: Whether the stream can encode the drawing symbols.
    """

    stream: TextIO
    can_rewrite: bool = False
    can_colour: bool = False
    can_draw: bool = False

    def paint(self, text: str, colour: str) -> str:
        """Wrap text in a colour, or hand it back untouched."""
        if not self.can_colour or not text:
            return text
        return f"{colour}{text}{RESET}"

    def line(self, text: str) -> None:
        """Write a line that stays."""
        prefix = ERASE_LINE if self.can_rewrite else ""
        self.stream.write(f"{prefix}{text}\n")
        self.stream.flush()

    def transient(self, text: str) -> None:
        """Draw a line that the next write replaces.

        Nothing is written where lines cannot be rewritten: a log file
        of half-finished steps, each one repeated at every spinner
        frame, is not a log file anybody wants.
        """
        if not self.can_rewrite:
            return
        self.stream.write(f"{ERASE_LINE}{text}")
        self.stream.flush()

    def clear(self) -> None:
        """Take back whatever transient line is on screen."""
        if not self.can_rewrite:
            return
        self.stream.write(ERASE_LINE)
        self.stream.flush()


def console_for(stream: TextIO, symbols: str = "") -> Console:
    """Ask a stream what it can do.

    Args:
        stream: Where the output is going.
        symbols: The characters a caller intends to draw with. They
            are tried against the stream's encoding, because a
            `UnicodeEncodeError` halfway through a build would be a
            progress display that broke the thing it was reporting on.
    """
    interactive = _is_interactive(stream)
    return Console(
        stream=stream,
        can_rewrite=interactive,
        can_colour=interactive and not os.environ.get("NO_COLOR"),
        can_draw=interactive and _encodes(stream, symbols),
    )


def _is_interactive(stream: TextIO) -> bool:
    """Whether a person is watching this stream in a terminal."""
    if os.environ.get("TERM") == DUMB_TERMINAL:
        return False
    try:
        return bool(stream.isatty())
    except (AttributeError, ValueError):
        return False


def _encodes(stream: TextIO, text: str) -> bool:
    """Whether the stream can carry these characters."""
    if not text:
        return True
    try:
        text.encode(getattr(stream, "encoding", None) or "ascii")
    except (LookupError, UnicodeEncodeError):
        return False
    return True
