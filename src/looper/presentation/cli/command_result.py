"""What a command hands back to the entry point."""

from __future__ import annotations

from dataclasses import dataclass

EXIT_SUCCESS = 0


@dataclass(frozen=True)
class CommandResult:
    """The output of a command and the exit code it implies.

    Most commands succeed or raise. ``run`` is different: it hands back the
    exit code of the simulation it started, which a caller in a script needs
    to see.

    Attributes:
        output: Text printed to standard output.
        exit_code: Exit code of the process.
    """

    output: str
    exit_code: int = EXIT_SUCCESS
