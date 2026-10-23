"""Rendering of use case reports as plain text."""

from __future__ import annotations

from collections.abc import Iterator

from looper.application.dto import (
    AdapterSurfaceReport,
    BuildSimulationReport,
    ContractGapSummary,
    GeneratedFileSummary,
    GenerateSimulationReport,
    ModuleSummary,
)

MODULE_COLUMN_WIDTH = 12
FILE_COLUMN_WIDTH = 24
NEWLINE = "\n"


def render_report(report: AdapterSurfaceReport) -> str:
    """Render an analysis report, including the contract gaps."""
    return NEWLINE.join(_render_lines(report))


def render_generation_report(report: GenerateSimulationReport) -> str:
    """Render the result of a generation run."""
    return NEWLINE.join(_render_generation_lines(report))


def _render_lines(report: AdapterSurfaceReport) -> Iterator[str]:
    """Produce the analysis report line by line."""
    yield f"Adapter surface: {report.header_directory}"
    yield ""
    yield from (_render_module(module) for module in report.modules)
    yield ""
    yield (
        f"{len(report.modules)} modules, {report.function_count} functions, "
        f"{report.extern_data_count} exported data symbols"
    )
    yield from _render_gaps(report)


def _render_module(module: ModuleSummary) -> str:
    """Render one module as a single aligned line."""
    counts = (
        f"functions={module.function_count:<3} records={module.record_count:<2} "
        f"enums={module.enum_count}"
    )
    if not module.extern_data_names:
        return f"  {module.name:<{MODULE_COLUMN_WIDTH}} {counts}"
    exported = ", ".join(module.extern_data_names)
    return f"  {module.name:<{MODULE_COLUMN_WIDTH}} {counts}  data={exported}"


def _render_gaps(report: AdapterSurfaceReport) -> Iterator[str]:
    """Render the contract gaps, or a confirmation that there are none."""
    if report.is_contract_complete:
        yield "Contract complete: every buffer and callback is specified."
        return
    yield ""
    yield f"{len(report.gaps)} declarations need a contract before generation:"
    yield from (f"  {_render_gap(gap)}" for gap in report.gaps)


def _render_gap(gap: ContractGapSummary) -> str:
    """Render one contract gap."""
    if gap.parameter_name is None:
        return f"{gap.function_name}  [{gap.reason}]"
    return f"{gap.function_name}.{gap.parameter_name}  [{gap.reason}]"


def _render_generation_lines(report: GenerateSimulationReport) -> Iterator[str]:
    """Produce the generation report line by line."""
    yield f"Generated into: {report.output_directory}"
    yield ""
    yield from (_render_generated_file(entry) for entry in report.files)
    yield ""
    yield f"{len(report.files)} files, {report.function_count} functions simulated"
    yield from _render_contract_warning(report)


def _render_generated_file(entry: GeneratedFileSummary) -> str:
    """Render one generated file as a single aligned line."""
    name = str(entry.relative_path)
    return f"  {name:<{FILE_COLUMN_WIDTH}} {entry.line_count:>5} lines  [{entry.kind}]"


def _render_contract_warning(report: GenerateSimulationReport) -> Iterator[str]:
    """Warn about parameters that were generated without a contract."""
    if not report.uncontracted_count:
        return
    yield (
        f"{report.uncontracted_count} parameters had no contract and were generated "
        "with the conservative default."
    )


def render_build_report(report: BuildSimulationReport) -> str:
    """Render the result of a build."""
    return NEWLINE.join(_render_build_lines(report))


def _render_build_lines(report: BuildSimulationReport) -> Iterator[str]:
    """Produce the build report line by line."""
    yield f"Built {report.name}"
    yield ""
    yield f"  executable  {report.executable}"
    yield f"  compiler    {report.compiler}"
    yield (
        f"  generated   {report.generated_file_count} files, "
        f"{report.function_count} adapter functions simulated"
    )
    yield from _render_contract_note(report)


def _render_contract_note(report: BuildSimulationReport) -> Iterator[str]:
    """Warn about parameters that were built without a contract."""
    if not report.uncontracted_count:
        return
    yield (
        f"{report.uncontracted_count} parameters had no contract and were built "
        "with the conservative default."
    )
