"""The simulation built by CMake instead of by looper-cli.

A firmware project that already uses CMake brings looper in as a dependency
and declares the simulation as one more target. Both ways have to produce a
simulation that runs, and the only way to know they do is to configure,
build and start one.

Two ways through: with the generator, which is the default, and without it
for a project that commits the generated sources and does not want the tool
in its build.
"""

from __future__ import annotations

import re
from pathlib import Path

from cmake_project import EXAMPLE, built, configure, configured, copied_project, runs

from looper.infrastructure.debug import DwarfDebugReader

LISTENING = "blinky listening on port"

# The SOURCES keyword together with the paths indented under it.
SOURCES_BLOCK = re.compile(r"\n\s*SOURCES(?:\n\s+\S+)+")


def test_cmake_generates_builds_and_runs_a_simulation(tmp_path: Path) -> None:
    """The whole path a firmware project would take."""
    build_directory = tmp_path / "with-generator"

    configured(build_directory)

    assert LISTENING in runs(built(build_directory))


def test_the_generator_writes_what_cmake_reads(tmp_path: Path) -> None:
    """CMake names the sources rather than globbing or guessing them."""
    configured(tmp_path / "manifest")
    manifest = EXAMPLE / "build" / "generated" / "looper_generated.cmake"

    content = manifest.read_text(encoding="utf-8")

    assert "sil_adapter_blinky.c" in content, "what the generator wrote"
    assert "src/app.c" in content, "what the definition names"
    assert "LOOPER_COMPILE_OPTIONS" in content, "the flags it asks for"


def test_a_project_can_leave_its_sources_to_the_definition(tmp_path: Path) -> None:
    """What a firmware with dozens of source directories does: name them once.

    Dropping SOURCES has to produce the same programme, because the
    definition already says which files take part.
    """
    project = copied_project(tmp_path)
    definition = project / "CMakeLists.txt"
    without_sources = SOURCES_BLOCK.sub("", definition.read_text(encoding="utf-8"))
    assert "SOURCES" not in without_sources, "the test did not remove what it meant to"
    definition.write_text(without_sources, encoding="utf-8")

    build_directory = tmp_path / "from-definition"
    completed = configure(project, build_directory)
    assert completed.returncode == 0, completed.stdout + completed.stderr

    assert LISTENING in runs(built(build_directory))


def test_a_project_can_build_without_the_generator(tmp_path: Path) -> None:
    """Committed sources and no Python in the build, which some teams want."""
    configured(tmp_path / "seed")
    build_directory = tmp_path / "without-generator"

    configured(build_directory, "-DLOOPER_GENERATE=OFF")

    assert LISTENING in runs(built(build_directory))


def test_a_build_without_generated_sources_says_what_to_do(tmp_path: Path) -> None:
    """The one mistake the switch invites, answered where it is made."""
    empty = tmp_path / "empty"
    empty.mkdir()
    project = copied_project(
        tmp_path,
        **{
            "GENERATED__${CMAKE_CURRENT_LIST_DIR}/build/generated": (
                f"GENERATED {empty.as_posix()}"
            )
        },
    )

    completed = configure(project, tmp_path / "unconfigurable", "-DLOOPER_GENERATE=OFF")

    assert completed.returncode != 0
    assert "No generated simulation at" in completed.stdout + completed.stderr


def test_both_build_paths_describe_the_same_programme(
    simulation_executable: Path, tmp_path: Path
) -> None:
    """The two ways through have to produce the same thing to look at.

    They compile the runtime differently -- one into the executable, the
    other as a library -- and a library built without debug information
    would quietly leave looper's own state out of the variable listing. The
    firmware would still be complete, which is what makes it the kind of
    difference nobody notices until they go looking for something.
    """
    build_directory = tmp_path / "parity"
    configured(build_directory)
    reader = DwarfDebugReader()

    directly = {variable.path.text for variable in reader.read_variables(simulation_executable)}
    through_cmake = {
        variable.path.text for variable in reader.read_variables(built(build_directory))
    }

    assert through_cmake == directly
