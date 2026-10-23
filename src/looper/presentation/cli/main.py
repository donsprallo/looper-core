"""Command line entry point."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from looper import __version__
from looper.application.errors import ContractIncompleteError, SimulationBuildFailedError
from looper.infrastructure.build import BuildDefinitionError, MissingCompilerError
from looper.infrastructure.contracts import ContractDefinitionError
from looper.infrastructure.parsing import HeaderParseError
from looper.presentation.cli.analyze_command import register_analyze_command
from looper.presentation.cli.audit_command import register_audit_command
from looper.presentation.cli.build_command import register_build_command, register_run_command
from looper.presentation.cli.command_result import CommandResult
from looper.presentation.cli.errors import UsageError
from looper.presentation.cli.generate_command import register_generate_command
from looper.presentation.program_name import program_name

DESCRIPTION = "Software in the loop testing for HAL adapter based firmware projects."
DEFAULT_PROGRAM_NAME = "looper"

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
HANDLED_ERRORS = (
    HeaderParseError,
    ContractDefinitionError,
    ContractIncompleteError,
    BuildDefinitionError,
    SimulationBuildFailedError,
    MissingCompilerError,
    FileNotFoundError,
    UsageError,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with every registered command."""
    parser = argparse.ArgumentParser(
        prog=program_name(DEFAULT_PROGRAM_NAME), description=DESCRIPTION
    )
    parser.add_argument("--version", action="version", version=f"looper {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    register_analyze_command(subparsers)
    register_generate_command(subparsers)
    register_build_command(subparsers)
    register_run_command(subparsers)
    register_audit_command(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run one command and report its outcome through the exit code."""
    arguments = build_parser().parse_args(argv)
    try:
        result: CommandResult = arguments.handler(arguments)
    except HANDLED_ERRORS as error:
        print(f"{program_name(DEFAULT_PROGRAM_NAME)}: {error}", file=sys.stderr)
        return EXIT_FAILURE
    print(result.output)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
