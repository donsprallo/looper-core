"""The object file each source of a simulation is compiled into.

A simulation used to be one compiler invocation over every source at
once, which is the shortest command line and the longest silence. One
invocation per unit says where it has got to, and keeps the firmware's
ninety units off a single core.

What that needs is a name for each object file. Two sources in
different directories are regularly called the same thing -- every
module has its `main.c` -- so the name carries a digest of where the
source came from. Same source, same object, every run.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from looper.domain.model.build import SimulationBuildDefinition
from looper.infrastructure.build.project_sources import generated_sources, project_sources
from looper.infrastructure.runtime_location import component_sources

#: Where the object files go, under the directory the executable is in.
OBJECTS_DIRECTORY = "objects"

#: Hexadecimal digits of the source path kept in an object's name.
#: Eight is four billion, against the hundred or so paths in a build.
DIGEST_LENGTH = 8

#: What the compiler writes its dependency list into.
DEPENDENCY_SUFFIX = ".d"

#: What the command that produced an object is kept in.
COMMAND_SUFFIX = ".cmd"

#: The record of the command that linked the executable. It lists
#: every object, so a unit added or removed changes it too.
LINK_RECORD = "link.cmd"


@dataclass(frozen=True)
class TranslationUnit:
    """One source and the object file it is compiled into.

    Two more files live beside the object, both written only when the
    compiler agreed: what it depended on, and what it was asked. The
    first answers whether a header changed, the second whether the
    flags did, and a unit is out of date when either says so.

    Attributes:
        source: The file handed to the compiler.
        object_file: Where its output goes.
    """

    source: Path
    object_file: Path

    @property
    def dependencies(self) -> Path:
        """Where the compiler records what this unit was built from."""
        return self.object_file.with_suffix(DEPENDENCY_SUFFIX)

    @property
    def command_record(self) -> Path:
        """Where the command that built it is kept, to compare next time."""
        return self.object_file.with_suffix(COMMAND_SUFFIX)


def translation_units(
    definition: SimulationBuildDefinition, runtime: tuple[Path, ...]
) -> tuple[TranslationUnit, ...]:
    """Every unit the simulation is built from, in a stable order.

    Args:
        definition: What is being built.
        runtime: The runtime sources this build takes, which depend on
            what it asked the linker to do.
    """
    directory = objects_directory(definition)
    sources = (
        *generated_sources(definition),
        *runtime,
        *component_sources(definition.components),
        *project_sources(definition),
    )
    return tuple(TranslationUnit(source, directory / object_name(source)) for source in sources)


def objects_directory(definition: SimulationBuildDefinition) -> Path:
    """Where this build keeps its object files."""
    return definition.executable.parent / OBJECTS_DIRECTORY


def link_record(definition: SimulationBuildDefinition) -> Path:
    """Where the command that linked the executable is kept."""
    return objects_directory(definition) / LINK_RECORD


def object_name(source: Path) -> str:
    """A name no other source in the build can take.

    The stem is kept in front so that a person looking in the
    directory can still tell what is what.
    """
    digest = hashlib.sha1(str(source.resolve()).encode("utf-8")).hexdigest()
    return f"{source.stem}-{digest[:DIGEST_LENGTH]}.o"
