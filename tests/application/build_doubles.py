"""The stand-ins a build or a run is driven with.

Shared by the two use cases that sit on top of them: one builds, the
other builds and then starts what came out. Neither test wants a
compiler, a generator or a process anywhere near it.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path, PurePosixPath

from looper.application.commands import BuildSimulation, GenerateSimulation
from looper.application.dto import GenerateSimulationReport, GenerateSimulationRequest
from looper.domain.model.build import BuildOutcome, SimulationBuildDefinition
from looper.domain.model.codegen import ArtifactKind, GeneratedArtifact
from looper.domain.ports import ProgressListener, SimulationBuilder, SimulationRunner
from looper.domain.repositories import BuildDefinitionRepository

DEFINITION_PATH = Path("looper.toml")
COMPILER = "gcc"
REJECTED = "undefined reference to adapter_demo_send"
ARTIFACT = GeneratedArtifact(
    relative_path=PurePosixPath("sil_adapter_demo.c"),
    kind=ArtifactKind.C_SOURCE,
    content="/* generated */\n",
)


def a_definition(tmp_path: Path, executable: Path | None = None) -> SimulationBuildDefinition:
    """A project rooted in a temporary directory."""
    return SimulationBuildDefinition(
        name="demo",
        header_directory=tmp_path / "Inc",
        generated_directory=tmp_path / "build" / "generated",
        executable=executable if executable is not None else tmp_path / "build" / "demo",
    )


class StubDefinitionRepository(BuildDefinitionRepository):
    """Hands out one definition and counts the asking."""

    def __init__(self, definition: SimulationBuildDefinition) -> None:
        self.loads = 0
        self._definition = definition

    def load(self, definition_path: Path) -> SimulationBuildDefinition:
        self.loads += 1
        return self._definition


class StubGenerate(GenerateSimulation):
    """Generation that writes nothing and announces nothing."""

    def __init__(self) -> None:
        self.requests: list[GenerateSimulationRequest] = []

    def execute(self, request: GenerateSimulationRequest) -> GenerateSimulationReport:
        self.requests.append(request)
        return GenerateSimulationReport(
            output_directory=request.output_directory,
            files=(),
            function_count=5,
            uncontracted_count=0,
        )


class StubBuilder(SimulationBuilder):
    """A compiler that agrees, or does not, and counts nothing else."""

    def __init__(
        self, succeeded: bool = True, unit_count: int = 0, recompiled_count: int = 0
    ) -> None:
        self.calls = 0
        self._succeeded = succeeded
        self._unit_count = unit_count
        self._recompiled_count = recompiled_count

    def build(self, definition: SimulationBuildDefinition) -> BuildOutcome:
        self.calls += 1
        return BuildOutcome(
            executable=definition.executable,
            succeeded=self._succeeded,
            compiler=COMPILER,
            diagnostics="" if self._succeeded else REJECTED,
            unit_count=self._unit_count,
            recompiled_count=self._recompiled_count,
        )


class RecordingRunner(SimulationRunner):
    """Writes down what was started, and with which arguments."""

    def __init__(self, exit_code: int = 0) -> None:
        self.arguments: tuple[str, ...] = ()
        self.started: Path | None = None
        self._exit_code = exit_code

    def run(self, executable: Path, arguments: Sequence[str]) -> int:
        self.started = executable
        self.arguments = tuple(arguments)
        return self._exit_code


def a_build(
    definition: SimulationBuildDefinition,
    builder: StubBuilder | None = None,
    generate: StubGenerate | None = None,
    progress: ProgressListener | None = None,
) -> BuildSimulation:
    """The build use case, over whichever stand-ins a test cares about."""
    return BuildSimulation(
        definition_repository=StubDefinitionRepository(definition),
        generate=generate if generate is not None else StubGenerate(),
        builder=builder if builder is not None else StubBuilder(),
        progress=progress,
    )
