"""Failures raised by the command line tool."""

from __future__ import annotations


class UsageError(ValueError):
    """A command was called in a way its arguments do not describe.

    Separate from what argparse rejects: these are combinations argparse
    accepts because each argument on its own is optional, and only the
    command knows which combinations mean something.
    """
