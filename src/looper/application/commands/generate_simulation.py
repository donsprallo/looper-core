"""Use case that generates a host simulation of an adapter surface."""

from __future__ import annotations

from pathlib import Path

from looper.application.dto import (
    GeneratedFileSummary,
    GenerateSimulationReport,
    GenerateSimulationRequest,
)
from looper.application.errors import ContractIncompleteError
from looper.application.progress import (
    READING_CONTRACT,
    READING_HEADERS,
    counted,
)
from looper.domain.model.c_api import AdapterSurface
from looper.domain.model.codegen import GeneratedArtifact
from looper.domain.model.contract import AdapterContract, ContractCoverage
from looper.domain.ports import AdapterSimulationGenerator, ProgressListener, SilentProgress
from looper.domain.repositories import (
    AdapterContractRepository,
    AdapterSurfaceRepository,
    GeneratedArtifactRepository,
)
from looper.domain.services import evaluate_contract_coverage

RENDERING = "Generating the simulation"
WRITING = "Writing the sources"

#: What this use case announces, in the order it announces it. A
#: caller that draws a bar has to know how many steps there will be
#: before the first one starts.
GENERATION_STEPS = (READING_HEADERS, READING_CONTRACT, RENDERING, WRITING)


class GenerateSimulation:
    """Writes the C sources that let firmware link against a simulated adapter.

    The contract is checked before anything is written. A simulation built from
    an incomplete contract compiles and behaves plausibly while getting buffer
    lifetimes wrong, which is harder to notice than a refusal.
    """

    def __init__(
        self,
        surface_repository: AdapterSurfaceRepository,
        contract_repository: AdapterContractRepository,
        generator: AdapterSimulationGenerator,
        artifact_repository: GeneratedArtifactRepository,
        progress: ProgressListener | None = None,
    ) -> None:
        self._surfaces = surface_repository
        self._contracts = contract_repository
        self._generator = generator
        self._artifacts = artifact_repository
        self._progress = progress if progress is not None else SilentProgress()

    def execute(self, request: GenerateSimulationRequest) -> GenerateSimulationReport:
        """Generate the simulation and write it to the output directory.

        Raises:
            ContractIncompleteError: If parameters lack a contract and the
                request does not accept the defaults.
            FileNotFoundError: If the header directory does not exist.
        """
        surface = self._read_surface(request.header_directory)
        contract, coverage = self._read_contract(request, surface)
        artifacts = self._render(surface, contract)
        self._write(request.output_directory, artifacts)
        return _build_report(request.output_directory, artifacts, surface, coverage)

    def _read_surface(self, header_directory: Path) -> AdapterSurface:
        """Read what the adapter declares."""
        self._progress.begin(READING_HEADERS)
        surface = self._surfaces.load(header_directory)
        self._progress.end(counted(len(surface.functions), "function"))
        return surface

    def _read_contract(
        self, request: GenerateSimulationRequest, surface: AdapterSurface
    ) -> tuple[AdapterContract, ContractCoverage]:
        """Read what the declarations mean, and refuse an incomplete answer."""
        self._progress.begin(READING_CONTRACT)
        contract = self._load_contract(request.contract_path)
        coverage = self._check_coverage(surface, contract, request.allow_incomplete_contract)
        self._progress.end(_coverage_summary(coverage))
        return contract, coverage

    def _render(
        self, surface: AdapterSurface, contract: AdapterContract
    ) -> tuple[GeneratedArtifact, ...]:
        """Turn the pair into the files that simulate the adapter."""
        self._progress.begin(RENDERING)
        artifacts = self._generator.generate(surface, contract)
        self._progress.end(counted(len(artifacts), "file"))
        return artifacts

    def _write(self, output_directory: Path, artifacts: tuple[GeneratedArtifact, ...]) -> None:
        """Put the files where the build expects them."""
        self._progress.begin(WRITING)
        self._artifacts.write_all(output_directory, artifacts)
        self._progress.end(str(output_directory))

    def _load_contract(self, contract_path: Path | None) -> AdapterContract:
        """Load the contract, or an empty one when none was requested."""
        if contract_path is None:
            return AdapterContract()
        return self._contracts.load(contract_path)

    def _check_coverage(
        self, surface: AdapterSurface, contract: AdapterContract, allow_incomplete: bool
    ) -> ContractCoverage:
        """Evaluate the contract and refuse while anything is unspecified.

        A stale entry does not block: it names something the headers no longer
        declare, which leaves nothing about the generated code undecided.
        """
        coverage = evaluate_contract_coverage(surface, contract)
        if coverage.is_specified or allow_incomplete:
            return coverage
        raise ContractIncompleteError(coverage)


def _coverage_summary(coverage: ContractCoverage) -> str:
    """What the contract check found, in a few words."""
    if coverage.is_specified:
        return "fully specified"
    return f"{counted(len(coverage.unspecified), 'parameter')} without a contract"


def _build_report(
    output_directory: Path,
    artifacts: tuple[GeneratedArtifact, ...],
    surface: AdapterSurface,
    coverage: ContractCoverage,
) -> GenerateSimulationReport:
    """Summarise what generation produced."""
    return GenerateSimulationReport(
        output_directory=output_directory,
        files=tuple(_summarise(artifact) for artifact in artifacts),
        function_count=len(surface.functions),
        uncontracted_count=len(coverage.unspecified),
        stale_count=len(coverage.stale),
    )


def _summarise(artifact: GeneratedArtifact) -> GeneratedFileSummary:
    """Summarise one generated file."""
    return GeneratedFileSummary(
        relative_path=artifact.relative_path,
        kind=artifact.kind.value,
        line_count=len(artifact.content.splitlines()),
    )
