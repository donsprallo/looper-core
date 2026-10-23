"""Which files of a project take part in a simulation build.

A build definition names directories; a build needs files. Resolving the one
into the other is the same question whether a compiler is invoked directly
or a build system is handed the answer, so it is asked in one place.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from looper.domain.model.build import SimulationBuildDefinition
from looper.infrastructure.runtime_location import runtime_sources

SOURCE_PATTERN = "*.c"

#: The unit holding the allocator wrappers. It refers to symbols a
#: linker only provides when it was asked to wrap, so a build that does
#: not ask leaves it out rather than failing to link.
WRAPPER_UNIT = "looper_heap_wrap.c"


def project_sources(definition: SimulationBuildDefinition) -> tuple[Path, ...]:
    """The firmware and device model sources, in a stable order.

    Excluded units are left out here rather than later: a file the project
    says does not belong in the build should not reach a build system at all.
    """
    return tuple(
        source
        for source in _globbed(definition.source_directories)
        if definition.includes_source(source)
    )


def generated_sources(definition: SimulationBuildDefinition) -> tuple[Path, ...]:
    """The sources the generator wrote, in a stable order."""
    return tuple(
        source
        for source in sorted(definition.generated_directory.glob(SOURCE_PATTERN))
        if definition.includes_source(source)
    )


def include_directories(definition: SimulationBuildDefinition) -> tuple[Path, ...]:
    """Every directory the firmware expects to find a header in."""
    return (
        definition.generated_directory,
        definition.header_directory,
        *definition.include_directories,
    )


def _globbed(directories: Iterable[Path]) -> list[Path]:
    """Every source file in the given directories, in a stable order."""
    found: list[Path] = []
    for directory in directories:
        found.extend(sorted(directory.glob(SOURCE_PATTERN)))
    return found


def runtime_units(track_allocations: bool = False) -> tuple[Path, ...]:
    """The runtime's sources, less what this build has no use for.

    A build system that links a library gets this for nothing: an
    object nothing references is never pulled in. A link over a list
    of objects has no such step, so the choice is made here instead.

    Args:
        track_allocations: Whether the link will wrap the allocator.
    """
    return tuple(
        source for source in runtime_sources() if track_allocations or (source.name != WRAPPER_UNIT)
    )
