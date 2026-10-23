"""Failures raised while building or running a simulation."""

from __future__ import annotations


class BuildDefinitionError(ValueError):
    """A build definition could not be translated into domain objects."""


class MissingCompilerError(RuntimeError):
    """No usable C compiler could be found."""
