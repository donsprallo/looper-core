"""Wiring and execution of the ``analyze`` command."""

from __future__ import annotations

import argparse
from pathlib import Path

from looper.application.dto import AnalyzeAdapterSurfaceRequest
from looper.application.queries import AnalyzeAdapterSurface
from looper.application.queries.analyze_adapter_surface import ANALYSIS_STEPS
from looper.infrastructure.contracts import TomlAdapterContractRepository
from looper.infrastructure.parsing import LibclangAdapterSurfaceRepository
from looper.presentation.cli.command_result import CommandResult
from looper.presentation.cli.front_end_arguments import add_front_end_arguments, parse_options
from looper.presentation.cli.progress import report_progress
from looper.presentation.cli.progress_arguments import add_progress_argument
from looper.presentation.cli.report_renderer import render_report


def register_analyze_command(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the ``analyze`` command and its arguments."""
    parser = subparsers.add_parser("analyze", help="report what an adapter directory declares")
    parser.add_argument("header_directory", type=Path, help="directory holding the adapter headers")
    add_front_end_arguments(parser)
    parser.add_argument(
        "--contract", type=Path, default=None, help="TOML contract definition to check against"
    )
    add_progress_argument(parser)
    parser.set_defaults(handler=run_analyze)


def run_analyze(arguments: argparse.Namespace) -> CommandResult:
    """Execute the analysis and render its report."""
    request = AnalyzeAdapterSurfaceRequest(
        header_directory=arguments.header_directory, contract_path=arguments.contract
    )
    title = f"analyze  {arguments.header_directory}"
    with report_progress(title, ANALYSIS_STEPS, arguments.quiet) as progress:
        use_case = AnalyzeAdapterSurface(
            surface_repository=LibclangAdapterSurfaceRepository(parse_options(arguments)),
            contract_repository=TomlAdapterContractRepository(),
            progress=progress,
        )
        report = use_case.execute(request)
    return CommandResult(render_report(report))
