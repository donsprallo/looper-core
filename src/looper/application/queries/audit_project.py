"""Use case that inspects a project without running it."""

from __future__ import annotations

from pathlib import Path

from looper.application.dto import AuditProjectRequest, AuditView, StaticMemoryView
from looper.application.mapping import build_audit_view, build_static_memory_view
from looper.application.progress import (
    READING_CONTRACT,
    READING_DEFINITION,
    READING_HEADERS,
    counted,
)
from looper.domain.model.analysis import FirmwareUsage
from looper.domain.model.build import SimulationBuildDefinition
from looper.domain.model.c_api import AdapterSurface
from looper.domain.model.contract import AdapterContract
from looper.domain.model.sources import SourceLayout
from looper.domain.ports import (
    DebugInformationReader,
    FirmwareUsageReader,
    ProgressListener,
    SilentProgress,
)
from looper.domain.repositories import (
    AdapterContractRepository,
    AdapterSurfaceRepository,
    BuildDefinitionRepository,
)
from looper.domain.services import describe_static_memory, inspect_project

READING_SOURCES = "Reading the firmware sources"
CHECKING = "Comparing the descriptions"
READING_BUILD = "Reading the build"

#: What an audit announces, in order.
AUDIT_STEPS = (
    READING_DEFINITION,
    READING_HEADERS,
    READING_CONTRACT,
    READING_SOURCES,
    CHECKING,
    READING_BUILD,
)


class AuditProject:
    """Reports what a project's own descriptions disagree about.

    Three things are read and compared: what the adapter declares, what
    the contract says it means, and what the project's sources do with
    it. Nothing is built and nothing is run, so this answers before a
    simulation exists as well as after.
    """

    def __init__(
        self,
        definition_repository: BuildDefinitionRepository,
        surface_repository: AdapterSurfaceRepository,
        contract_repository: AdapterContractRepository,
        usage_reader: FirmwareUsageReader,
        debug_reader: DebugInformationReader | None = None,
        layout: SourceLayout | None = None,
        progress: ProgressListener | None = None,
    ) -> None:
        self._definitions = definition_repository
        self._surfaces = surface_repository
        self._contracts = contract_repository
        self._usage = usage_reader
        self._debug = debug_reader
        self._layout = layout if layout is not None else SourceLayout()
        self._progress = progress if progress is not None else SilentProgress()

    def execute(self, request: AuditProjectRequest) -> AuditView:
        """Inspect the project the request names.

        Raises:
            FileNotFoundError: If the definition or the headers are absent.
        """
        definition = self._read_definition(request.definition_path)
        surface = self._read_surface(definition.header_directory)
        contract = self._read_contract(definition.contract_path)
        usage = self._read_usage(definition, surface)
        view = self._check(surface, contract, usage)
        memory, note = self._read_build(definition)
        return view.model_copy(update={"static_memory": memory, "memory_note": note})

    def _read_definition(self, definition_path: Path) -> SimulationBuildDefinition:
        """Read what the project says it is."""
        self._progress.begin(READING_DEFINITION)
        definition = self._definitions.load(definition_path)
        self._progress.end(definition.name)
        return definition

    def _read_surface(self, header_directory: Path) -> AdapterSurface:
        """Read what the adapter declares."""
        self._progress.begin(READING_HEADERS)
        surface = self._surfaces.load(header_directory)
        self._progress.end(counted(len(surface.functions), "function"))
        return surface

    def _read_contract(self, contract_path: Path | None) -> AdapterContract:
        """Read what the declarations mean, or an empty contract."""
        self._progress.begin(READING_CONTRACT)
        contract = self._load_contract(contract_path)
        self._progress.end(_contract_summary(contract_path, contract))
        return contract

    def _read_usage(
        self, definition: SimulationBuildDefinition, surface: AdapterSurface
    ) -> FirmwareUsage:
        """Read what the project's own sources do with the adapter."""
        self._progress.begin(READING_SOURCES)
        usage = self._usage.read(definition, _names_of(surface))
        self._progress.end(_usage_summary(usage))
        return usage

    def _check(
        self, surface: AdapterSurface, contract: AdapterContract, usage: FirmwareUsage
    ) -> AuditView:
        """Compare the three descriptions against each other."""
        self._progress.begin(CHECKING)
        view = build_audit_view(inspect_project(surface, contract, usage))
        self._progress.end(counted(len(view.findings), "finding"))
        return view

    def _read_build(
        self, definition: SimulationBuildDefinition
    ) -> tuple[StaticMemoryView | None, str]:
        """Read what the built simulation holds, announcing the attempt."""
        self._progress.begin(READING_BUILD)
        memory, note = self._static_memory(definition)
        self._progress.end(note if memory is None else counted(memory.object_count, "object"))
        return memory, note

    def _load_contract(self, contract_path: Path | None) -> AdapterContract:
        """Load the contract, or an empty one when the project has none."""
        if contract_path is None:
            return AdapterContract()
        return self._contracts.load(contract_path)

    def _static_memory(
        self, definition: SimulationBuildDefinition
    ) -> tuple[StaticMemoryView | None, str]:
        """What the built simulation holds, when there is one to read.

        The rest of the audit needs no build: it reads headers, a
        contract and sources. This one part needs the executable,
        because only a compiler knows how big a structure came out. So
        it is reported when there is a build and plainly left out when
        there is not, rather than quietly reading nothing.
        """
        if self._debug is None:
            return None, ""
        if not definition.executable.is_file():
            return None, (
                f"no build at {definition.executable.name}, so what it would hold "
                "statically is not known yet"
            )
        try:
            symbols = self._debug.read_statics(definition.executable)
        except (OSError, ValueError) as error:
            return None, f"the build carries no sizes to read: {error}"
        report = describe_static_memory(symbols, self._layout, definition.memory_budget)
        return build_static_memory_view(report), ""


def _contract_summary(contract_path: Path | None, contract: AdapterContract) -> str:
    """What the contract turned out to say, in a few words.

    A project with no contract and a project with an empty one are
    both legitimate and are not the same thing, so they do not read
    the same either.
    """
    if contract_path is None:
        return "the project has none"
    if not contract.functions and not contract.roles:
        return "empty, nothing needs describing"
    return f"{counted(len(contract.functions), 'function')}, {counted(len(contract.roles), 'role')}"


def _usage_summary(usage: FirmwareUsage) -> str:
    """How much of the project could be read, in a few words."""
    if not usage.units_unreadable:
        return counted(usage.units_read, "unit")
    return f"{counted(usage.units_read, 'unit')}, {usage.units_unreadable} unreadable"


def _names_of(surface: AdapterSurface) -> frozenset[str]:
    """Every function name the adapter declares."""
    return frozenset(function.name for function in surface.functions)
