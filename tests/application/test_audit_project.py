"""What the audit use case reads, and what it hands back.

The checks themselves are the domain's; what is tested here is the
assembly: that the project's own definition decides which headers,
which contract and which sources are read, and that what comes back is
something a report can print without knowing any of that.
"""

from __future__ import annotations

from pathlib import Path

from looper.application.dto import AuditProjectRequest
from looper.application.queries import AuditProject
from looper.application.queries.audit_project import AUDIT_STEPS
from looper.domain.model.analysis import FirmwareUsage
from looper.domain.model.build import SimulationBuildDefinition
from looper.domain.model.c_api import (
    AdapterModule,
    AdapterSurface,
    CExternData,
    CFunction,
    CType,
    CTypeKind,
)
from looper.domain.model.contract import AdapterContract
from looper.domain.ports import FirmwareUsageReader
from looper.domain.repositories import (
    AdapterContractRepository,
    AdapterSurfaceRepository,
    BuildDefinitionRepository,
)
from progress_doubles import RecordingProgress

VOID = CType(spelling="void", kind=CTypeKind.VOID)
TABLE = CType(spelling="demo_interface_t", kind=CTypeKind.RECORD)
RESET = CFunction(name="adapter_demo_reset", return_type=VOID)

DEFINITION = SimulationBuildDefinition(
    name="demo",
    header_directory=Path("Inc"),
    generated_directory=Path("build/generated"),
    executable=Path("build/demo"),
    contract_path=Path("contract.toml"),
)


class DefinitionRepository(BuildDefinitionRepository):
    """Hands out one definition and remembers what was asked for."""

    def __init__(self) -> None:
        self.asked_for: list[Path] = []

    def load(self, definition_path: Path) -> SimulationBuildDefinition:
        self.asked_for.append(definition_path)
        return DEFINITION


class SurfaceRepository(AdapterSurfaceRepository):
    """Hands out one surface and remembers which directory was read."""

    def __init__(self) -> None:
        self.asked_for: list[Path] = []

    def load(self, header_directory: Path) -> AdapterSurface:
        self.asked_for.append(header_directory)
        module = AdapterModule(
            name="demo",
            header_path=Path("Inc/adapter_demo.h"),
            functions=(RESET,),
            extern_data=(CExternData("demo_interface", TABLE),),
        )
        return AdapterSurface(modules=(module,))


class ContractRepository(AdapterContractRepository):
    """Hands out an empty contract and remembers it was asked."""

    def __init__(self) -> None:
        self.asked_for: list[Path] = []

    def load(self, contract_path: Path) -> AdapterContract:
        self.asked_for.append(contract_path)
        return AdapterContract()


class UsageReader(FirmwareUsageReader):
    """Reports a project that reaches nothing, and remembers the question."""

    def __init__(self) -> None:
        self.wanted: frozenset[str] = frozenset()

    def read(self, definition: SimulationBuildDefinition, wanted: frozenset[str]) -> FirmwareUsage:
        self.wanted = wanted
        return FirmwareUsage(units_read=3)


def _audit(
    progress: RecordingProgress | None = None,
) -> tuple[AuditProject, SurfaceRepository, ContractRepository, UsageReader]:
    """The use case and the doubles it was assembled from."""
    surfaces, contracts, usage = SurfaceRepository(), ContractRepository(), UsageReader()
    use_case = AuditProject(
        definition_repository=DefinitionRepository(),
        surface_repository=surfaces,
        contract_repository=contracts,
        usage_reader=usage,
        progress=progress,
    )
    return use_case, surfaces, contracts, usage


def test_the_project_definition_says_what_to_read() -> None:
    use_case, surfaces, contracts, usage = _audit()

    use_case.execute(AuditProjectRequest(definition_path=Path("looper.toml")))

    assert surfaces.asked_for == [Path("Inc")]
    assert contracts.asked_for == [Path("contract.toml")]
    assert usage.wanted == frozenset({"adapter_demo_reset"})


def test_the_findings_come_back_ready_to_print() -> None:
    use_case, _, _, _ = _audit()

    view = use_case.execute(AuditProjectRequest(definition_path=Path("looper.toml")))

    assert view.of_kind("exported_data_without_initialiser")[0].subject == "demo_interface"
    assert view.of_kind("never_called")[0].subject == "adapter_demo_reset"
    assert view.coverage_note == "read all 3 translation units"
    assert not view.is_clean


def test_a_finding_that_is_only_worth_knowing_is_kept_apart() -> None:
    use_case, _, _, _ = _audit()

    view = use_case.execute(AuditProjectRequest(definition_path=Path("looper.toml")))

    assert [finding.subject for finding in view.notes] == ["adapter_demo_reset"]
    assert [finding.subject for finding in view.defects] == ["demo_interface"]


def test_an_audit_announces_exactly_the_steps_it_published() -> None:
    """Six steps are easy to drift from; the plan is what draws the bar."""
    progress = RecordingProgress()
    use_case, _, _, _ = _audit(progress)

    use_case.execute(AuditProjectRequest(definition_path=Path("looper.toml")))

    assert tuple(progress.announced) == AUDIT_STEPS
    assert progress.open_steps == 0
