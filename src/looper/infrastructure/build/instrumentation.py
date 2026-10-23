"""The flags that let the compiler weave a profiler into a simulation.

Asking the compiler to call a hook on every function entry and return is
one flag. Keeping it off the three parts that must not be woven is the
other, and it is the one that matters.

The generated adapter is already measured at its boundary, where it can
also say whether anything answered a call; instrumenting it as well
would put every adapter function into two reports with two slightly
different numbers. The runtime is the apparatus doing the measuring, and
a profiler that profiles itself reports mostly itself. The components
ship compiled into the same binary but are not the project's code.

What is left is exactly what was asked for: the firmware and the device
model standing in for its board.
"""

from __future__ import annotations

from looper.domain.model.build import SimulationBuildDefinition
from looper.infrastructure.runtime_location import components_root, runtime_root

INSTRUMENT_FLAG = "-finstrument-functions"

#: The allocator calls looper puts itself in front of.
WRAPPED_ALLOCATORS = ("malloc", "free", "calloc", "realloc")
EXCLUDE_FLAG = "-finstrument-functions-exclude-file-list="


def instrumentation_options(definition: SimulationBuildDefinition) -> tuple[str, ...]:
    """The compiler options a profiled build adds, or nothing.

    Args:
        definition: The build, which says whether it wants a profile.

    Returns:
        The options, in the order they go on the command line.
    """
    if not definition.profile:
        return ()
    return (INSTRUMENT_FLAG, EXCLUDE_FLAG + ",".join(excluded_directories(definition)))


def excluded_directories(definition: SimulationBuildDefinition) -> tuple[str, ...]:
    """The directories whose sources must not be woven.

    The exclusion is a substring match on the path of each file as the
    compiler was handed it, so a directory spelled one way here and
    another way there excludes nothing at all. On Windows the two build
    paths disagree about the spelling -- a direct build passes
    backslashes and CMake passes forward slashes -- so both are listed.
    An extra substring that matches nothing costs nothing.
    """
    directories = (definition.generated_directory, runtime_root(), components_root())
    spellings = [
        spelling for directory in directories for spelling in (str(directory), directory.as_posix())
    ]
    return tuple(dict.fromkeys(spellings))


def allocation_link_options(definition: SimulationBuildDefinition) -> tuple[str, ...]:
    """The link options that put looper in front of the allocator.

    A link time switch rather than a compile time one: no source
    changes, and the wrappers are in the runtime either way. What this
    decides is only which ``malloc`` a call reaches.

    Args:
        definition: The build, which says whether it wants to watch.

    Returns:
        The options, or nothing when it does not.
    """
    if not definition.track_allocations:
        return ()
    return tuple(f"-Wl,--wrap={name}" for name in WRAPPED_ALLOCATORS)
