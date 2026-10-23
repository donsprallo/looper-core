"""Behaviour of the simulation generation use case."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path, PurePosixPath

import pytest

from looper.application.commands import GenerateSimulation
from looper.application.commands.generate_simulation import GENERATION_STEPS
from looper.application.dto import GenerateSimulationRequest
from looper.application.errors import ContractIncompleteError
from looper.domain.model.c_api import (
    AdapterModule,
    AdapterSurface,
    CFunction,
    CParameter,
    CType,
    CTypeKind,
)
from looper.domain.model.codegen import ArtifactKind, GeneratedArtifact
from looper.domain.model.contract import (
    AdapterContract,
    FunctionContract,
    ParameterContract,
    ParameterRole,
)
from looper.domain.ports import AdapterSimulationGenerator
from looper.domain.repositories import (
    AdapterContractRepository,
    AdapterSurfaceRepository,
    GeneratedArtifactRepository,
)
from progress_doubles import RecordingProgress

BOOLEAN = CType(spelling="bool", kind=CTypeKind.BOOLEAN)
BYTE = CType(spelling="uint8_t", kind=CTypeKind.INTEGER)
BYTE_POINTER = CType(spelling="uint8_t *", kind=CTypeKind.POINTER, pointee=BYTE)

SEND = CFunction(
    name="adapter_demo_send", return_type=BOOLEAN, parameters=(CParameter("data", BYTE_POINTER),)
)
SURFACE = AdapterSurface(
    modules=(AdapterModule(name="demo", header_path=Path("Inc/adapter_demo.h"), functions=(SEND,)),)
)
COMPLETE_CONTRACT = AdapterContract(
    functions=(
        FunctionContract(
            function_name="adapter_demo_send",
            parameters=(ParameterContract(parameter_name="data", role=ParameterRole.INPUT),),
        ),
    )
)
ARTIFACT = GeneratedArtifact(
    relative_path=PurePosixPath("sil_adapter_demo.c"),
    kind=ArtifactKind.C_SOURCE,
    content="/* generated */\n",
)


class StubSurfaceRepository(AdapterSurfaceRepository):
    def load(self, header_directory: Path) -> AdapterSurface:
        return SURFACE


class StubContractRepository(AdapterContractRepository):
    def __init__(self, contract: AdapterContract) -> None:
        self._contract = contract

    def load(self, contract_path: Path) -> AdapterContract:
        return self._contract


class StubGenerator(AdapterSimulationGenerator):
    def generate(
        self, surface: AdapterSurface, contract: AdapterContract
    ) -> tuple[GeneratedArtifact, ...]:
        return (ARTIFACT,)


class RecordingArtifactRepository(GeneratedArtifactRepository):
    def __init__(self) -> None:
        self.written: list[GeneratedArtifact] = []

    def write_all(self, output_directory: Path, artifacts: Sequence[GeneratedArtifact]) -> None:
        self.written.extend(artifacts)


def _use_case(
    contract: AdapterContract,
    artifacts: RecordingArtifactRepository,
    progress: RecordingProgress | None = None,
) -> GenerateSimulation:
    return GenerateSimulation(
        surface_repository=StubSurfaceRepository(),
        contract_repository=StubContractRepository(contract),
        generator=StubGenerator(),
        artifact_repository=artifacts,
        progress=progress,
    )


def _request(**overrides: object) -> GenerateSimulationRequest:
    values: dict[str, object] = {
        "header_directory": Path("Inc"),
        "output_directory": Path("out"),
        "contract_path": Path("contract.toml"),
    }
    values.update(overrides)
    return GenerateSimulationRequest.model_validate(values)


def test_a_complete_contract_is_generated_and_written() -> None:
    artifacts = RecordingArtifactRepository()

    report = _use_case(COMPLETE_CONTRACT, artifacts).execute(_request())

    assert [str(entry.relative_path) for entry in report.files] == ["sil_adapter_demo.c"]
    assert report.uncontracted_count == 0
    assert artifacts.written == [ARTIFACT]


def test_an_incomplete_contract_refuses_and_writes_nothing() -> None:
    artifacts = RecordingArtifactRepository()

    with pytest.raises(ContractIncompleteError, match="adapter_demo_send.data"):
        _use_case(AdapterContract(), artifacts).execute(_request())

    assert artifacts.written == []


def test_an_incomplete_contract_may_be_accepted_explicitly() -> None:
    artifacts = RecordingArtifactRepository()

    report = _use_case(AdapterContract(), artifacts).execute(
        _request(allow_incomplete_contract=True)
    )

    assert report.uncontracted_count == 1
    assert artifacts.written == [ARTIFACT]


def test_generation_announces_exactly_the_steps_it_published() -> None:
    """The plan a command draws a bar against is the plan that happens."""
    progress = RecordingProgress()

    _use_case(COMPLETE_CONTRACT, RecordingArtifactRepository(), progress).execute(_request())

    assert tuple(progress.announced) == GENERATION_STEPS
    assert progress.open_steps == 0


def test_every_step_says_what_it_came_to() -> None:
    progress = RecordingProgress()

    _use_case(COMPLETE_CONTRACT, RecordingArtifactRepository(), progress).execute(_request())

    assert progress.summaries[:3] == ["1 function", "fully specified", "1 file"]


def test_a_step_that_refuses_is_left_open_rather_than_reported_as_done() -> None:
    """Whoever is drawing the display closes it as the failure it was."""
    progress = RecordingProgress()
    use_case = _use_case(AdapterContract(), RecordingArtifactRepository(), progress)

    with pytest.raises(ContractIncompleteError):
        use_case.execute(_request())

    assert progress.announced[-1] == GENERATION_STEPS[1]
    assert progress.open_steps == 1
