"""The name an entry point was invoked under."""

from __future__ import annotations

import sys
from pathlib import Path


def program_name(fallback: str) -> str:
    """Return the command name to show in help output.

    An entry point can be reachable under more than one name, so the name is
    taken from the invocation rather than hard coded. The extension is dropped
    so that help output reads the same on Windows as elsewhere.

    Args:
        fallback: Name to use when the invocation carries none.

    Returns:
        The command name, for example ``looper-cli``.
    """
    invoked = Path(sys.argv[0]).stem if sys.argv and sys.argv[0] else ""
    return invoked or fallback
