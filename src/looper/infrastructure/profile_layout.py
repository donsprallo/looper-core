"""Where the parts of a simulation keep their sources, as far as is known.

A client attached to a running simulation over a socket knows two things
for certain: where the looper runtime lives and where its components do,
because they were installed alongside the client itself. It does not
know which directory holds the firmware and which holds the device
model, because that is written in a build definition it was never
given.

Both answers are useful, and the second is the better one. A client that
reads the project's definition can tell the device model from the
firmware; one that cannot still tells both from the machinery, and the
directories underneath show the difference plainly enough.
"""

from __future__ import annotations

from pathlib import PurePath

from looper.domain.model.build import SimulationBuildDefinition
from looper.domain.model.sources import SourceLayout
from looper.infrastructure.runtime_location import components_root, runtime_root


def default_source_layout() -> SourceLayout:
    """What a client knows without being shown a build definition."""
    return SourceLayout(runtime=(runtime_root(),), components=(components_root(),))


def layout_of(definition: SimulationBuildDefinition) -> SourceLayout:
    """What a client knows once it has read the project's definition.

    The device model is the project's own source: the directories that
    lie beside the definition file. Everything else it points at is the
    firmware, which is somewhere else by the nature of the arrangement
    -- looper never asks a firmware project to hold a device model.

    A project that points at nothing outside itself is the exception,
    and it is what the small examples look like: firmware and model in
    one directory, with nothing to separate them by. Splitting there
    would label a firmware as a device model, so nothing is split and
    all of it is called firmware.
    """
    project = definition.project_root
    if project is None:
        return default_source_layout()
    inside, outside = _split_by(definition.source_directories, project)
    if not outside:
        inside, outside = (), inside
    return SourceLayout(
        adapter=(definition.generated_directory,),
        runtime=(runtime_root(),),
        components=(components_root(),),
        device_model=inside,
        firmware=outside,
    )


def _split_by(
    directories: tuple[PurePath, ...], project: PurePath
) -> tuple[tuple[PurePath, ...], tuple[PurePath, ...]]:
    """Separate the directories inside a project from the ones outside."""
    inside = tuple(one for one in directories if _is_under(one, project))
    outside = tuple(one for one in directories if not _is_under(one, project))
    return inside, outside


def _is_under(directory: PurePath, project: PurePath) -> bool:
    """Whether a directory lies within the project, however it is spelled."""
    folded = str(directory).replace("/", "\\").casefold()
    claimed = str(project).replace("/", "\\").casefold().rstrip("\\")
    return folded.startswith(claimed + "\\")
