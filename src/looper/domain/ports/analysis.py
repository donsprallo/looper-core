"""Abstract outbound interface for reading what a project does."""

from __future__ import annotations

from abc import ABC, abstractmethod

from looper.domain.model.analysis import FirmwareUsage
from looper.domain.model.build.build_definition import SimulationBuildDefinition


class FirmwareUsageReader(ABC):
    """Reads a project's own sources to see how it uses its adapter."""

    @abstractmethod
    def read(self, definition: SimulationBuildDefinition, wanted: frozenset[str]) -> FirmwareUsage:
        """Report what the project does with the given functions.

        Args:
            definition: The project, as its build definition describes it.
            wanted: Adapter function names worth looking for.

        Returns:
            What was found, including how much could be read.
        """
