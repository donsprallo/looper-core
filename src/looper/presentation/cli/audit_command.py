"""Wiring and execution of the ``audit`` command."""

from __future__ import annotations

import argparse
from pathlib import Path

from looper.application.dto import AuditProjectRequest
from looper.application.queries import AuditProject
from looper.application.queries.audit_project import AUDIT_STEPS
from looper.infrastructure.analysis import LibclangFirmwareUsageReader
from looper.infrastructure.build import DEFAULT_FILE_NAME, TomlBuildDefinitionRepository
from looper.infrastructure.contracts import TomlAdapterContractRepository
from looper.infrastructure.debug import DwarfDebugReader
from looper.infrastructure.parsing import LibclangAdapterSurfaceRepository
from looper.infrastructure.profile_layout import layout_of
from looper.presentation.cli.audit_renderer import render_audit
from looper.presentation.cli.build_command import surface_parse_options
from looper.presentation.cli.command_result import CommandResult
from looper.presentation.cli.progress import report_progress
from looper.presentation.cli.progress_arguments import add_progress_argument

EXIT_DEFECTS_FOUND = 1


def register_audit_command(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the ``audit`` command and its arguments."""
    parser = subparsers.add_parser(
        "audit", help="inspect a project against its contract without running it"
    )
    parser.add_argument(
        "definition",
        type=Path,
        nargs="?",
        default=Path(DEFAULT_FILE_NAME),
        help=f"build definition to inspect, default {DEFAULT_FILE_NAME}",
    )
    add_progress_argument(parser)
    parser.set_defaults(handler=run_audit)


def run_audit(arguments: argparse.Namespace) -> CommandResult:
    """Inspect the project and report what was found.

    The exit code is what a build server reads: anything to act on makes
    the command fail, so an audit can stand in a pipeline unattended.
    """
    definitions = TomlBuildDefinitionRepository()
    definition = definitions.load(arguments.definition)
    title = f"audit  {arguments.definition}"
    with report_progress(title, AUDIT_STEPS, arguments.quiet) as progress:
        use_case = AuditProject(
            definition_repository=definitions,
            surface_repository=LibclangAdapterSurfaceRepository(surface_parse_options(definition)),
            contract_repository=TomlAdapterContractRepository(),
            usage_reader=LibclangFirmwareUsageReader(),
            debug_reader=DwarfDebugReader(),
            layout=layout_of(definition),
            progress=progress,
        )
        view = use_case.execute(AuditProjectRequest(definition_path=arguments.definition))
    exit_code = 0 if view.has_nothing_to_act_on else EXIT_DEFECTS_FOUND
    return CommandResult(render_audit(view), exit_code)
