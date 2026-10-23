"""The one argument every command shares about the progress display.

It is per command rather than on the program, because `looper build
--quiet` is what a person types and `looper --quiet build` is what
argparse would otherwise insist on.
"""

from __future__ import annotations

import argparse


def add_progress_argument(parser: argparse.ArgumentParser) -> None:
    """Let a command be asked to work without saying anything."""
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="work without the progress display",
    )
