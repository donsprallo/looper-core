"""The outbound interfaces that compile a simulation and start it."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path

from looper.domain.model.build.build_definition import SimulationBuildDefinition
from looper.domain.model.build.build_outcome import BuildOutcome


class SimulationBuilder(ABC):
    """Compiles a generated simulation into an executable."""

    @abstractmethod
    def build(self, definition: SimulationBuildDefinition) -> BuildOutcome:
        """Compile and link every source the definition names.

        Args:
            definition: What to build and how.

        Returns:
            What the compiler run produced, successful or not. A build that the
            compiler rejected is an outcome, not an exception.

        Raises:
            RuntimeError: If no usable compiler is available at all.
        """


class SimulationRunner(ABC):
    """Starts a built simulation and waits for it to finish."""

    @abstractmethod
    def run(self, executable: Path, arguments: Sequence[str]) -> int:
        """Run the executable until it stops.

        Args:
            executable: Simulation to start.
            arguments: Arguments passed to it.

        Returns:
            The exit code of the simulation.
        """
