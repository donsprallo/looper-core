"""Wiring and execution of the ``build`` and ``run`` commands."""

from __future__ import annotations

import argparse
from pathlib import Path

from looper.application.commands import BuildSimulation, GenerateSimulation, RunSimulation
from looper.application.commands.build_simulation import BUILD_STEPS
from looper.application.dto import BuildSimulationRequest, RunSimulationRequest
from looper.domain.model.build import SimulationBuildDefinition
from looper.domain.ports import ProgressListener, SilentProgress
from looper.infrastructure.build import (
    DEFAULT_FILE_NAME,
    CompilerSimulationBuilder,
    SubprocessSimulationRunner,
    TomlBuildDefinitionRepository,
    write_cmake_manifest,
)
from looper.infrastructure.codegen import CSimulationGenerator
from looper.infrastructure.contracts import TomlAdapterContractRepository
from looper.infrastructure.filesystem import FileSystemArtifactRepository
from looper.infrastructure.parsing import LibclangAdapterSurfaceRepository, ParseOptions
from looper.presentation.cli.command_result import CommandResult
from looper.presentation.cli.progress import report_progress
from looper.presentation.cli.progress_arguments import add_progress_argument
from looper.presentation.cli.report_renderer import render_build_report

RUN_EXIT_PREFIX = "simulation exited with code"


def register_build_command(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the ``build`` command and its arguments."""
    parser = subparsers.add_parser("build", help="generate and compile a simulation")
    _add_definition_argument(parser)
    parser.set_defaults(handler=run_build)


def register_run_command(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the ``run`` command and its arguments."""
    parser = subparsers.add_parser("run", help="build a simulation and start it")
    _add_definition_argument(parser)
    parser.add_argument("--port", type=int, default=None, help="port the simulation listens on")
    parser.add_argument(
        "--virtual", action="store_true", help="run on a virtual clock instead of the host clock"
    )
    parser.add_argument(
        "--no-build", action="store_true", help="start the existing executable unchanged"
    )
    parser.set_defaults(handler=run_run)


def _add_definition_argument(parser: argparse.ArgumentParser) -> None:
    """Add the arguments every build based command shares."""
    parser.add_argument(
        "definition",
        type=Path,
        nargs="?",
        default=Path(DEFAULT_FILE_NAME),
        help=f"build definition to use, default {DEFAULT_FILE_NAME}",
    )
    parser.add_argument(
        "--allow-incomplete-contract",
        action="store_true",
        help="build although parameters still lack a contract",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="compile every translation unit, up to date or not",
    )
    add_progress_argument(parser)


def run_build(arguments: argparse.Namespace) -> CommandResult:
    """Generate and compile the simulation, then report what was produced."""
    request = BuildSimulationRequest(
        definition_path=arguments.definition,
        allow_incomplete_contract=arguments.allow_incomplete_contract,
    )
    with report_progress(_title("build", arguments), BUILD_STEPS, arguments.quiet) as progress:
        use_case = _build_use_case(arguments.definition, progress, arguments.rebuild)
        report = use_case.execute(request)
        # So that a project which later switches to CMake does not read a
        # manifest describing a build from before.
        write_cmake_manifest(TomlBuildDefinitionRepository().load(arguments.definition))
    return CommandResult(render_build_report(report))


def run_run(arguments: argparse.Namespace) -> CommandResult:
    """Build the simulation and run it until it stops."""
    request = RunSimulationRequest(
        definition_path=arguments.definition,
        port=arguments.port,
        virtual_time=arguments.virtual,
        skip_build=arguments.no_build,
        allow_incomplete_contract=arguments.allow_incomplete_contract,
    )
    # Nothing is announced when the build is skipped, so a display that
    # would show a title and then six steps that never happen is not
    # started at all.
    silent = arguments.quiet or arguments.no_build
    with report_progress(_title("run", arguments), BUILD_STEPS, silent) as progress:
        runner = SubprocessSimulationRunner()
        use_case = _build_use_case(arguments.definition, progress, arguments.rebuild)
        exit_code = RunSimulation(use_case, runner).execute(request)
    return CommandResult(f"{RUN_EXIT_PREFIX} {exit_code}", exit_code)


def _title(command: str, arguments: argparse.Namespace) -> str:
    """What the display says it is working on."""
    return f"{command}  {arguments.definition}"


def _build_use_case(
    definition_path: Path, progress: ProgressListener | None = None, rebuild: bool = False
) -> BuildSimulation:
    """Assemble the build use case from its concrete collaborators.

    The definition is read here as well as inside the use case, because the
    compiler front end has to be configured with the include directories the
    project declares before the use case can run.
    """
    definitions = TomlBuildDefinitionRepository()
    options = surface_parse_options(definitions.load(definition_path))
    listener = progress if progress is not None else SilentProgress()
    return BuildSimulation(
        definition_repository=definitions,
        generate=GenerateSimulation(
            surface_repository=LibclangAdapterSurfaceRepository(options),
            contract_repository=TomlAdapterContractRepository(),
            generator=CSimulationGenerator(),
            artifact_repository=FileSystemArtifactRepository(),
            progress=listener,
        ),
        builder=CompilerSimulationBuilder(listener, rebuild),
        progress=listener,
    )


def surface_parse_options(definition: SimulationBuildDefinition) -> ParseOptions:
    """Build the front end configuration a project declares for its headers."""
    return ParseOptions(
        include_directories=definition.parse_include_directories,
        definitions=definition.parse_definitions,
    )
