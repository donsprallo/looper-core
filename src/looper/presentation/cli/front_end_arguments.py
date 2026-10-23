"""Command line arguments shared by every command that parses headers."""

from __future__ import annotations

import argparse
from pathlib import Path

from looper.infrastructure.parsing import ParseOptions


def add_front_end_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the arguments that configure the compiler front end."""
    parser.add_argument(
        "-I",
        "--include",
        type=Path,
        action="append",
        default=[],
        dest="include_directories",
        metavar="DIR",
        help="additional include directory, repeatable",
    )
    parser.add_argument(
        "-D",
        "--define",
        action="append",
        default=[],
        dest="definitions",
        metavar="NAME[=VALUE]",
        help="preprocessor definition, repeatable",
    )


def parse_options(arguments: argparse.Namespace) -> ParseOptions:
    """Build the front end configuration from the parsed command line."""
    return ParseOptions(
        include_directories=tuple(arguments.include_directories),
        definitions=tuple(arguments.definitions),
    )
