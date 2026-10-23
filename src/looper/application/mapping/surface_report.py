"""Mapping of domain objects onto the analysis report."""

from __future__ import annotations

from pathlib import Path

from looper.application.dto.adapter_surface_report import (
    AdapterSurfaceReport,
    ContractGapSummary,
    ModuleSummary,
)
from looper.domain.model.c_api import AdapterModule, AdapterSurface
from looper.domain.model.contract import ContractCoverage, ContractGap


def build_surface_report(
    header_directory: Path, surface: AdapterSurface, coverage: ContractCoverage
) -> AdapterSurfaceReport:
    """Translate a parsed surface and its coverage into a report."""
    return AdapterSurfaceReport(
        header_directory=header_directory,
        modules=tuple(_summarise_module(module) for module in surface.modules),
        gaps=tuple(_summarise_gap(gap) for gap in coverage.gaps),
    )


def _summarise_module(module: AdapterModule) -> ModuleSummary:
    """Translate one parsed module into its summary."""
    return ModuleSummary(
        name=module.name,
        header_path=module.header_path,
        function_count=len(module.functions),
        record_count=len(module.records),
        enum_count=len(module.enums),
        extern_data_names=tuple(symbol.name for symbol in module.extern_data),
    )


def _summarise_gap(gap: ContractGap) -> ContractGapSummary:
    """Translate one contract gap into its summary."""
    return ContractGapSummary(
        function_name=gap.function_name,
        reason=gap.reason.value,
        parameter_name=gap.parameter_name,
    )
