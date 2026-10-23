"""Use case that generates and compiles a simulation."""

from __future__ import annotations

from pathlib import Path

from looper.application.commands.generate_simulation import (
    GENERATION_STEPS,
    GenerateSimulation,
)
from looper.application.dto import (
    BuildSimulationReport,
    BuildSimulationRequest,
    GenerateSimulationRequest,
)
from looper.application.errors import SimulationBuildFailedError
from looper.application.progress import READING_DEFINITION, counted
from looper.domain.model.build import BuildOutcome, SimulationBuildDefinition
from looper.domain.ports import ProgressListener, SilentProgress, SimulationBuilder
from looper.domain.repositories import BuildDefinitionRepository

COMPILING = "Compiling and linking"

#: What a build announces, in order: reading the project, everything
#: generation does, and then the compiler.
BUILD_STEPS = (READING_DEFINITION, *GENERATION_STEPS, COMPILING)


class BuildSimulation:
    """Turns a firmware project into a runnable simulation.

    Generation and compilation are one step on purpose. Generated sources are
    an intermediate product, and a build that stops between the two leaves a
    directory whose contents nobody should edit.
    """

    def __init__(
        self,
        definition_repository: BuildDefinitionRepository,
        generate: GenerateSimulation,
        builder: SimulationBuilder,
        progress: ProgressListener | None = None,
    ) -> None:
        self._definitions = definition_repository
        self._generate = generate
        self._builder = builder
        self._progress = progress if progress is not None else SilentProgress()

    def execute(self, request: BuildSimulationRequest) -> BuildSimulationReport:
        """Generate the adapter simulation and compile the executable.

        Raises:
            FileNotFoundError: If the definition or the headers are missing.
            ContractIncompleteError: If parameters lack a contract and the
                request does not accept the defaults.
            SimulationBuildFailedError: If the compiler rejected the result.
            MissingCompilerError: If no usable compiler can be found.
        """
        definition = self._read_definition(request.definition_path)
        generated = self._generate.execute(_generation_request(definition, request))
        outcome = self._compile(definition)
        return BuildSimulationReport(
            name=definition.name,
            executable=outcome.executable,
            compiler=outcome.compiler,
            generated_file_count=len(generated.files),
            function_count=generated.function_count,
            uncontracted_count=generated.uncontracted_count,
        )

    def _read_definition(self, definition_path: Path) -> SimulationBuildDefinition:
        """Read what the project says it is."""
        self._progress.begin(READING_DEFINITION)
        definition = self._definitions.load(definition_path)
        self._progress.end(definition.name)
        return definition

    def _compile(self, definition: SimulationBuildDefinition) -> BuildOutcome:
        """Hand everything to the compiler, and insist that it agreed.

        Raises:
            SimulationBuildFailedError: If the compiler rejected the result.
        """
        self._progress.begin(COMPILING)
        outcome = self._builder.build(definition)
        if not outcome.succeeded:
            raise SimulationBuildFailedError(outcome.compiler, outcome.diagnostics)
        self._progress.end(_compiled_summary(definition, outcome))
        return outcome

    def definition(self, request: BuildSimulationRequest) -> SimulationBuildDefinition:
        """Read the definition without building anything."""
        return self._definitions.load(request.definition_path)


def _compiled_summary(definition: SimulationBuildDefinition, outcome: BuildOutcome) -> str:
    """What the compiler came to, in a few words.

    How much was skipped is the interesting part of an incremental
    build: a reader who changed one file wants to see that one file
    was compiled, and a reader who changed a header wants to see how
    far it reached.
    """
    if not outcome.unit_count:
        return definition.executable.name
    return f"{definition.executable.name}, {_units_text(outcome)}"


def _units_text(outcome: BuildOutcome) -> str:
    """How many units were compiled, out of how many there are."""
    if not outcome.recompiled_count:
        return f"{counted(outcome.unit_count, 'unit')} unchanged"
    if outcome.recompiled_count == outcome.unit_count:
        return counted(outcome.unit_count, "unit")
    return f"{outcome.recompiled_count} of {counted(outcome.unit_count, 'unit')}"


def _generation_request(
    definition: SimulationBuildDefinition, request: BuildSimulationRequest
) -> GenerateSimulationRequest:
    """Translate a build request into the generation it implies."""
    return GenerateSimulationRequest(
        header_directory=definition.header_directory,
        output_directory=definition.generated_directory,
        contract_path=definition.contract_path,
        allow_incomplete_contract=request.allow_incomplete_contract,
    )
