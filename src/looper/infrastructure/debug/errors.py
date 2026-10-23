"""Failures encountered while reading debug information."""

from __future__ import annotations


class DebugInformationError(ValueError):
    """An executable carries no debug information this reader can use."""
