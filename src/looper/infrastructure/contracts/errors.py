"""Failures raised while reading a contract definition."""

from __future__ import annotations


class ContractDefinitionError(ValueError):
    """A contract definition could not be translated into domain objects."""
