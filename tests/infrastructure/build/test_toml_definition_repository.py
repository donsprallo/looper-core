"""Reading a build definition from TOML."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from looper.infrastructure.build import BuildDefinitionError, TomlBuildDefinitionRepository

MINIMAL = """
[simulation]
name = "demo"
headers = "Inc"
"""

COMPLETE = """
[simulation]
name = "demo"
headers = "Inc"
contract = "contract.toml"
sources = ["src", "bsp"]
includes = ["Inc", "src"]
defines = ["DEMO=1"]
generated = "out/generated"
executable = "out/demo.elf"
parse_includes = ["../shared/Inc"]
parse_defines = ["__PIC32MZ"]
compiler = "clang"
standard = "c17"
warnings = ["-Wall"]
record_calls = false
"""


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "looper.toml"
    path.write_text(content, encoding="utf-8")
    return path


def test_a_missing_definition_is_reported(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="No build definition"):
        TomlBuildDefinitionRepository().load(tmp_path / "absent.toml")


def test_the_minimum_is_a_name_and_a_header_directory(tmp_path: Path) -> None:
    definition = TomlBuildDefinitionRepository().load(_write(tmp_path, MINIMAL))

    assert definition.name == "demo"
    assert definition.header_directory == (tmp_path / "Inc").resolve()
    assert definition.contract_path is None


def test_paths_resolve_against_the_definition_not_the_working_directory(
    tmp_path: Path,
) -> None:
    definition = TomlBuildDefinitionRepository().load(_write(tmp_path, COMPLETE))

    assert definition.source_directories == (
        (tmp_path / "src").resolve(),
        (tmp_path / "bsp").resolve(),
    )
    assert definition.parse_include_directories == ((tmp_path / "../shared/Inc").resolve(),)


def test_every_setting_is_read(tmp_path: Path) -> None:
    definition = TomlBuildDefinitionRepository().load(_write(tmp_path, COMPLETE))

    assert definition.compiler == "clang"
    assert definition.language_standard == "c17"
    assert definition.warning_flags == ("-Wall",)
    assert definition.parse_definitions == ("__PIC32MZ",)
    assert not definition.record_calls


def test_call_recording_adds_its_definition_only_when_enabled(tmp_path: Path) -> None:
    recording = TomlBuildDefinitionRepository().load(_write(tmp_path, MINIMAL))
    silent = TomlBuildDefinitionRepository().load(_write(tmp_path, COMPLETE))

    assert "LOOPER_JOURNAL" in recording.all_definitions
    assert "LOOPER_JOURNAL" not in silent.all_definitions
    assert silent.all_definitions == ("DEMO=1",)


def test_the_defaults_land_under_build(tmp_path: Path) -> None:
    definition = TomlBuildDefinitionRepository().load(_write(tmp_path, MINIMAL))

    assert definition.generated_directory == tmp_path / "build" / "generated"
    assert definition.executable.parent == tmp_path / "build"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows executable naming")
def test_an_executable_without_a_suffix_gets_one_on_windows(tmp_path: Path) -> None:
    definition = TomlBuildDefinitionRepository().load(_write(tmp_path, MINIMAL))

    assert definition.executable.name == "demo.exe"


def test_an_explicit_suffix_is_kept(tmp_path: Path) -> None:
    definition = TomlBuildDefinitionRepository().load(_write(tmp_path, COMPLETE))

    assert definition.executable.name == "demo.elf"


def test_a_missing_name_is_reported(tmp_path: Path) -> None:
    with pytest.raises(BuildDefinitionError, match="required key 'name'"):
        TomlBuildDefinitionRepository().load(_write(tmp_path, '[simulation]\nheaders = "Inc"\n'))


def test_a_missing_section_is_reported(tmp_path: Path) -> None:
    with pytest.raises(BuildDefinitionError, match=r"\[simulation\] table"):
        TomlBuildDefinitionRepository().load(_write(tmp_path, '[other]\nname = "demo"\n'))


def test_an_unknown_key_is_reported(tmp_path: Path) -> None:
    definition = '[simulation]\nname = "d"\nheaders = "Inc"\nsourcs = ["src"]\n'

    with pytest.raises(BuildDefinitionError, match="Unknown keys.*sourcs"):
        TomlBuildDefinitionRepository().load(_write(tmp_path, definition))


def test_a_wrongly_typed_value_is_reported(tmp_path: Path) -> None:
    definition = '[simulation]\nname = "d"\nheaders = "Inc"\nrecord_calls = "yes"\n'

    with pytest.raises(BuildDefinitionError, match="must be true or false"):
        TomlBuildDefinitionRepository().load(_write(tmp_path, definition))


def test_excluded_sources_are_resolved_and_honoured(tmp_path: Path) -> None:
    definition = '[simulation]\nname = "d"\nheaders = "Inc"\nexclude = ["app/legacy.c"]\n'

    loaded = TomlBuildDefinitionRepository().load(_write(tmp_path, definition))

    excluded = (tmp_path / "app" / "legacy.c").resolve()
    assert loaded.excluded_sources == (excluded,)
    assert not loaded.includes_source(excluded)
    assert loaded.includes_source(tmp_path / "app" / "kept.c")
