"""The commands a simulation build issues, and what came back.

Two kinds: one compile per translation unit, and one link over every
object. They are written down here rather than in the builder so that
what goes on a command line can be read, and tested, without running
a compiler.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from looper.domain.model.build import SimulationBuildDefinition
from looper.infrastructure.build.instrumentation import (
    allocation_link_options,
    instrumentation_options,
)
from looper.infrastructure.build.project_sources import include_directories
from looper.infrastructure.build.translation_units import TranslationUnit
from looper.infrastructure.runtime_location import runtime_include_directories

WINDOWS_SOCKET_LIBRARY = "-lws2_32"
MATH_LIBRARY = "-lm"
COMPILE_ONLY = "-c"
OUTPUT_FLAG = "-o"

#: Write, beside the object, the list of files it was built from,
#: leaving out the system headers. It is what the next build reads to
#: decide whether this unit still has to be compiled.
DEPENDENCY_FLAGS = ("-MMD", "-MF")


@dataclass(frozen=True)
class CompilerReply:
    """What one invocation of the compiler came to.

    Attributes:
        succeeded: Whether it returned zero.
        diagnostics: What it had to say, errors and warnings alike.
    """

    succeeded: bool
    diagnostics: str


def compile_command(
    compiler: str, definition: SimulationBuildDefinition, unit: TranslationUnit
) -> list[str]:
    """Everything needed to turn one source into one object file."""
    command = [compiler, definition.standard_flag, *definition.warning_flags]
    command.extend(instrumentation_options(definition))
    command.extend(f"-D{value}" for value in definition.all_definitions)
    command.extend([*DEPENDENCY_FLAGS, str(unit.dependencies)])
    command.extend([COMPILE_ONLY, str(unit.source), OUTPUT_FLAG, str(unit.object_file)])
    command.extend(f"-I{directory}" for directory in _include_directories(definition))
    return command


def link_command(
    compiler: str, definition: SimulationBuildDefinition, units: tuple[TranslationUnit, ...]
) -> list[str]:
    """Everything needed to turn the object files into the executable.

    The warning flags are carried over although nothing is compiled
    here. A project may have put something on that line that the
    linker wants, and a flag the linker ignores costs nothing.
    """
    command = [compiler, *definition.warning_flags, OUTPUT_FLAG, str(definition.executable)]
    command.extend(str(unit.object_file) for unit in units)
    command.extend(allocation_link_options(definition))
    command.append(WINDOWS_SOCKET_LIBRARY if sys.platform == "win32" else MATH_LIBRARY)
    return command


def run_compiler(command: list[str]) -> CompilerReply:
    """Run one command and keep what it said.

    A compiler that rejects its input is an outcome rather than an
    exception: the diagnostics are the answer the caller wanted.
    """
    completed = subprocess.run(command, capture_output=True, text=True, check=False)  # noqa: S603
    return CompilerReply(
        succeeded=completed.returncode == 0,
        diagnostics=(completed.stderr or completed.stdout).strip(),
    )


def _include_directories(definition: SimulationBuildDefinition) -> list[Path]:
    """Collect every include directory the compiler needs."""
    return [*include_directories(definition), *runtime_include_directories()]
