"""Abstract outbound interfaces for reading and writing generation inputs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path

from looper.domain.model.build.build_definition import SimulationBuildDefinition
from looper.domain.model.c_api.adapter_surface import AdapterSurface
from looper.domain.model.codegen.generated_artifact import GeneratedArtifact
from looper.domain.model.contract.adapter_contract import AdapterContract


class AdapterSurfaceRepository(ABC):
    """Reads adapter declarations from a directory of HAL headers."""

    @abstractmethod
    def load(self, header_directory: Path) -> AdapterSurface:
        """Parse every adapter header below the given directory.

        Args:
            header_directory: Directory holding the adapter headers.

        Returns:
            The complete declared API surface.

        Raises:
            FileNotFoundError: If the directory does not exist.
        """


class AdapterContractRepository(ABC):
    """Reads the hand written semantics that complement the declarations."""

    @abstractmethod
    def load(self, contract_path: Path) -> AdapterContract:
        """Read the contract definition for one adapter surface.

        Args:
            contract_path: Path of the contract definition.

        Returns:
            The parsed contract. A missing optional contract yields an empty one.
        """


class GeneratedArtifactRepository(ABC):
    """Writes generated files to their destination."""

    @abstractmethod
    def write_all(self, output_directory: Path, artifacts: Sequence[GeneratedArtifact]) -> None:
        """Write every artifact below the given output root.

        Args:
            output_directory: Root the artifact paths are resolved against.
            artifacts: Files to write.
        """


class BuildDefinitionRepository(ABC):
    """Reads the definition of how a project builds its simulation."""

    @abstractmethod
    def load(self, definition_path: Path) -> SimulationBuildDefinition:
        """Read one build definition.

        Args:
            definition_path: Path of the definition file.

        Returns:
            The definition with every path resolved against its directory.

        Raises:
            FileNotFoundError: If the definition does not exist.
        """
