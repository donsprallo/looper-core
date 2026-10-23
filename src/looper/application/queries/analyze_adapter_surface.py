"""Use case that analyses a directory of adapter headers."""

from __future__ import annotations

from pathlib import Path

from looper.application.dto import AdapterSurfaceReport, AnalyzeAdapterSurfaceRequest
from looper.application.mapping import build_surface_report
from looper.application.progress import (
    READING_CONTRACT,
    READING_HEADERS,
    counted,
)
from looper.domain.model.contract import AdapterContract
from looper.domain.ports import ProgressListener, SilentProgress
from looper.domain.repositories import AdapterContractRepository, AdapterSurfaceRepository
from looper.domain.services import evaluate_contract_coverage

#: What an analysis announces, in order.
ANALYSIS_STEPS = (READING_HEADERS, READING_CONTRACT)


class AnalyzeAdapterSurface:
    """Reports what a simulation of an adapter directory would have to provide.

    The use case answers two questions in one pass: what the adapter declares,
    and which of those declarations still lack the semantics that generation
    needs. Both repositories are abstract, so the use case runs against a real
    front end and against a test double alike.
    """

    def __init__(
        self,
        surface_repository: AdapterSurfaceRepository,
        contract_repository: AdapterContractRepository,
        progress: ProgressListener | None = None,
    ) -> None:
        self._surfaces = surface_repository
        self._contracts = contract_repository
        self._progress = progress if progress is not None else SilentProgress()

    def execute(self, request: AnalyzeAdapterSurfaceRequest) -> AdapterSurfaceReport:
        """Analyse the requested header directory.

        Raises:
            FileNotFoundError: If the header directory does not exist.
        """
        self._progress.begin(READING_HEADERS)
        surface = self._surfaces.load(request.header_directory)
        self._progress.end(counted(len(surface.functions), "function"))
        self._progress.begin(READING_CONTRACT)
        contract = self._load_contract(request.contract_path)
        coverage = evaluate_contract_coverage(surface, contract)
        self._progress.end("fully specified" if coverage.is_specified else "incomplete")
        return build_surface_report(request.header_directory, surface, coverage)

    def _load_contract(self, contract_path: Path | None) -> AdapterContract:
        """Load the contract, or an empty one when none was requested."""
        if contract_path is None:
            return AdapterContract()
        return self._contracts.load(contract_path)
