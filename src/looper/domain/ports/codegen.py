"""The outbound interface that turns an adapter surface into sources."""

from __future__ import annotations

from abc import ABC, abstractmethod

from looper.domain.model.c_api.adapter_surface import AdapterSurface
from looper.domain.model.codegen.generated_artifact import GeneratedArtifact
from looper.domain.model.contract.adapter_contract import AdapterContract


class AdapterSimulationGenerator(ABC):
    """Turns a declared adapter surface into the files that simulate it."""

    @abstractmethod
    def generate(
        self, surface: AdapterSurface, contract: AdapterContract
    ) -> tuple[GeneratedArtifact, ...]:
        """Render every file the simulation consists of.

        Args:
            surface: Declarations the simulation has to satisfy.
            contract: Semantics the declarations do not express.

        Returns:
            The generated files, described but not yet written anywhere.
        """
