"""Wiring and execution of the ``generate`` command."""

from __future__ import annotations

import argparse
from pathlib import Path

from looper.application.commands import GenerateSimulation
from looper.application.commands.generate_simulation import GENERATION_STEPS
from looper.application.dto import GenerateSimulationRequest
from looper.domain.model.build import SimulationBuildDefinition
from looper.domain.ports import ProgressListener
from looper.infrastructure.build import TomlBuildDefinitionRepository, write_cmake_manifest
from looper.infrastructure.codegen import CSimulationGenerator
from looper.infrastructure.contracts import TomlAdapterContractRepository
from looper.infrastructure.filesystem import FileSystemArtifactRepository
from looper.infrastructure.parsing import LibclangAdapterSurfaceRepository, ParseOptions
from looper.presentation.cli.command_result import CommandResult
from looper.presentation.cli.errors import UsageError
from looper.presentation.cli.front_end_arguments import add_front_end_arguments, parse_options
from looper.presentation.cli.progress import report_progress
from looper.presentation.cli.progress_arguments import add_progress_argument
from looper.presentation.cli.report_renderer import render_generation_report


def register_generate_command(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the ``generate`` command and its arguments."""
    parser = subparsers.add_parser("generate", help="write a host simulation of an adapter")
    _add_input_arguments(parser)
    _add_output_argument(parser)
    add_front_end_arguments(parser)
    _add_contract_arguments(parser)
    add_progress_argument(parser)
    parser.set_defaults(handler=run_generate)


def _add_input_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the two ways of saying what to generate from."""
    parser.add_argument(
        "header_directory",
        type=Path,
        nargs="?",
        default=None,
        help="directory holding the adapter headers",
    )
    parser.add_argument(
        "--definition",
        type=Path,
        default=None,
        help="build definition to take the headers, contract and output from",
    )


def _add_output_argument(parser: argparse.ArgumentParser) -> None:
    """Add where the generated sources go."""
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        dest="output_directory",
        help="directory the generated sources are written to",
    )


def _add_contract_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the arguments that control contract checking."""
    parser.add_argument(
        "--contract", type=Path, default=None, help="TOML contract definition to generate from"
    )
    parser.add_argument(
        "--allow-incomplete-contract",
        action="store_true",
        help="generate although parameters still lack a contract",
    )


def run_generate(arguments: argparse.Namespace) -> CommandResult:
    """Execute the generation and render its report."""
    definition, request, options = _what_to_generate(arguments)
    title = f"generate  {request.header_directory}"
    with report_progress(title, GENERATION_STEPS, arguments.quiet) as progress:
        report = _use_case(options, progress).execute(request)
        if definition is not None:
            write_cmake_manifest(definition)
    return CommandResult(render_generation_report(report))


def _what_to_generate(
    arguments: argparse.Namespace,
) -> tuple[SimulationBuildDefinition | None, GenerateSimulationRequest, ParseOptions]:
    """Take the job from a build definition, or from the command line.

    Raises:
        UsageError: If neither says what to read and where to write it.
    """
    if arguments.definition is None:
        return None, _request_from_arguments(arguments), parse_options(arguments)
    definition = TomlBuildDefinitionRepository().load(arguments.definition)
    options = ParseOptions(
        include_directories=definition.parse_include_directories,
        definitions=definition.parse_definitions,
    )
    return definition, _request_from_definition(definition, arguments), options


def _use_case(options: ParseOptions, progress: ProgressListener) -> GenerateSimulation:
    """Assemble the generation from its concrete collaborators."""
    return GenerateSimulation(
        surface_repository=LibclangAdapterSurfaceRepository(options),
        contract_repository=TomlAdapterContractRepository(),
        generator=CSimulationGenerator(),
        artifact_repository=FileSystemArtifactRepository(),
        progress=progress,
    )


def _request_from_definition(
    definition: SimulationBuildDefinition, arguments: argparse.Namespace
) -> GenerateSimulationRequest:
    """Take what to generate from a build definition.

    A build system that already has a definition should not have to repeat
    the header directory and the output in its own language: two places that
    say where the headers are will eventually disagree.
    """
    return GenerateSimulationRequest(
        header_directory=definition.header_directory,
        output_directory=definition.generated_directory,
        contract_path=definition.contract_path,
        allow_incomplete_contract=arguments.allow_incomplete_contract,
    )


def _request_from_arguments(arguments: argparse.Namespace) -> GenerateSimulationRequest:
    """Take what to generate from the command line.

    Raises:
        UsageError: If the headers or the output were not named.
    """
    if arguments.header_directory is None or arguments.output_directory is None:
        raise UsageError(
            "Name a header directory and --output, or pass --definition to take both "
            "from a build definition."
        )
    return GenerateSimulationRequest(
        header_directory=arguments.header_directory,
        output_directory=arguments.output_directory,
        contract_path=arguments.contract,
        allow_incomplete_contract=arguments.allow_incomplete_contract,
    )
