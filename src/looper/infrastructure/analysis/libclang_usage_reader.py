"""Reading what a project does with its adapter, using the C front end.

The build definition already says where the sources are, which headers
they include and what the compiler defines. An inspection needs exactly
the same answers, so it is configured from the same place rather than
from a second list that would drift from the first.

The generated sources are read along with the project's own. They are
where a build definition's initialisers end up, so leaving them out
would report a table as empty that the build in fact fills.
"""

from __future__ import annotations

from looper.domain.model.analysis import FirmwareUsage
from looper.domain.model.build import SimulationBuildDefinition
from looper.domain.ports import FirmwareUsageReader
from looper.domain.services.project_inspection import INITIALISER_PREFIX
from looper.infrastructure.analysis.firmware_scanner import FirmwareScanner
from looper.infrastructure.build.project_sources import (
    generated_sources,
    include_directories,
    project_sources,
)
from looper.infrastructure.parsing.parse_options import ParseOptions
from looper.infrastructure.runtime_location import runtime_include_directories


class LibclangFirmwareUsageReader(FirmwareUsageReader):
    """Reads a project's sources with the same front end as the headers."""

    def read(self, definition: SimulationBuildDefinition, wanted: frozenset[str]) -> FirmwareUsage:
        """Scan every source of the project for the wanted functions."""
        scanner = FirmwareScanner(_parse_options(definition))
        sources = (*generated_sources(definition), *project_sources(definition))
        scan = scanner.scan(sources, wanted)
        return FirmwareUsage(
            call_sites=scan.call_sites,
            reached_functions=scan.reached_functions,
            answered_functions=scan.hooked_functions,
            initialised_data=_initialised_data(definition),
            units_read=scan.units_read,
            units_unreadable=scan.units_unreadable,
        )


def _parse_options(definition: SimulationBuildDefinition) -> ParseOptions:
    """Configure the front end the way the build configures the compiler."""
    return ParseOptions(
        include_directories=(
            *include_directories(definition),
            *runtime_include_directories(),
            *definition.parse_include_directories,
        ),
        definitions=(*definition.all_definitions, *definition.parse_definitions),
    )


def _initialised_data(definition: SimulationBuildDefinition) -> frozenset[str]:
    """Exported symbols the build gives a value of its own."""
    return frozenset(
        definition_text[len(INITIALISER_PREFIX) :].split("=")[0]
        for definition_text in definition.all_definitions
        if definition_text.startswith(INITIALISER_PREFIX)
    )
