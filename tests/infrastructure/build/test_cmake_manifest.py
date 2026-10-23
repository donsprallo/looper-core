"""What a build definition says, rendered for another build system.

CMake cannot read a TOML definition and must not be made to repeat one, so
the manifest is the one place the two build paths meet. What it says has to
be exactly what the compiler invocation would have been given: the same
files, the same exclusions, the same flags.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from looper.domain.model.build import SimulationBuildDefinition
from looper.infrastructure.build.cmake_manifest import render_cmake_manifest


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A project with a generated directory and two source directories."""
    for directory, names in (
        ("build/generated", ("looper_hooks.c", "sil_adapter_demo.c")),
        ("src", ("main.c", "device_model.c")),
        ("firmware", ("app.c", "legacy.c")),
    ):
        made = tmp_path / directory
        made.mkdir(parents=True)
        for name in names:
            (made / name).write_text("/* */\n", encoding="utf-8")
    (tmp_path / "Inc").mkdir()
    return tmp_path


def a_definition(project: Path, **overrides: object) -> SimulationBuildDefinition:
    """A definition over the fixture project, with fields replaced."""
    arguments: dict[str, object] = {
        "name": "demo",
        "header_directory": project / "Inc",
        "generated_directory": project / "build" / "generated",
        "executable": project / "build" / "demo",
        "source_directories": (project / "src", project / "firmware"),
        "include_directories": (project / "Inc",),
    }
    arguments.update(overrides)
    return SimulationBuildDefinition(**arguments)  # type: ignore[arg-type]


def test_the_generated_sources_are_named_so_cmake_need_not_glob(project: Path) -> None:
    rendered = render_cmake_manifest(a_definition(project))

    assert "looper_hooks.c" in rendered
    assert "sil_adapter_demo.c" in rendered


def test_the_firmware_sources_come_from_the_definition(project: Path) -> None:
    rendered = render_cmake_manifest(a_definition(project))

    assert "src/main.c" in rendered
    assert "firmware/app.c" in rendered


def test_an_excluded_unit_does_not_reach_the_build_system(project: Path) -> None:
    """A file the project says is out should not be offered to CMake at all."""
    definition = a_definition(project, excluded_sources=(project / "firmware" / "legacy.c",))

    rendered = render_cmake_manifest(definition)

    assert "firmware/app.c" in rendered
    assert "legacy.c" not in rendered


def test_paths_are_written_the_way_cmake_reads_them(project: Path) -> None:
    """CMake takes a backslash as an escape, so a Windows path needs care."""
    rendered = render_cmake_manifest(a_definition(project))

    assert "\\" not in rendered


def test_the_flags_the_definition_asks_for_are_carried(project: Path) -> None:
    """Without these a CMake build would quietly differ from a direct one."""
    definition = a_definition(project, warning_flags=("-Wall", "-g"), language_standard="c17")

    rendered = render_cmake_manifest(definition)

    assert '"-Wall"' in rendered
    assert '"-g"' in rendered
    assert '"17"' in rendered


def test_the_journal_switch_reaches_the_compiler(project: Path) -> None:
    with_journal = render_cmake_manifest(a_definition(project, record_calls=True))
    without = render_cmake_manifest(a_definition(project, record_calls=False))

    assert "LOOPER_JOURNAL" in with_journal
    assert "LOOPER_JOURNAL" not in without


def test_every_include_directory_the_firmware_needs_is_listed(project: Path) -> None:
    rendered = render_cmake_manifest(a_definition(project))

    assert "build/generated" in rendered
    assert "/Inc" in rendered


def test_an_empty_list_is_still_a_list(project: Path) -> None:
    """CMake reads an unset variable as nothing, which is not the same."""
    rendered = render_cmake_manifest(a_definition(project, source_directories=()))

    assert "set(LOOPER_PROJECT_SOURCES)" in rendered
