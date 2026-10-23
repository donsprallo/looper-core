"""Build definition repository backed by a TOML file."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path
from typing import Any

from looper.domain.model.build import SimulationBuildDefinition
from looper.domain.model.build.build_definition import (
    DEFAULT_LANGUAGE_STANDARD,
    DEFAULT_WARNING_FLAGS,
)
from looper.domain.repositories import BuildDefinitionRepository
from looper.infrastructure.build.errors import BuildDefinitionError

SECTION = "simulation"
DEFAULT_FILE_NAME = "looper.toml"
DEFAULT_GENERATED_DIRECTORY = "build/generated"
DEFAULT_EXECUTABLE_DIRECTORY = "build"
EXECUTABLE_SUFFIX = ".exe" if sys.platform == "win32" else ""

KNOWN_KEYS = frozenset(
    {
        "name",
        "headers",
        "contract",
        "sources",
        "exclude",
        "includes",
        "defines",
        "generated",
        "executable",
        "parse_includes",
        "parse_defines",
        "compiler",
        "standard",
        "warnings",
        "record_calls",
        "components",
        "profile",
        "memory_budget",
        "track_allocations",
    }
)


class TomlBuildDefinitionRepository(BuildDefinitionRepository):
    """Reads a ``looper.toml`` describing one simulation build.

    Every path in the file is relative to the file itself, so a definition can
    be checked in next to the firmware and used from any working directory.
    """

    def load(self, definition_path: Path) -> SimulationBuildDefinition:
        """Read the definition and resolve its paths.

        Raises:
            FileNotFoundError: If the definition does not exist.
            BuildDefinitionError: If the file is malformed.
        """
        if not definition_path.is_file():
            raise FileNotFoundError(f"No build definition at '{definition_path}'")
        section = _read_section(definition_path)
        return _build(section, definition_path.parent.resolve())


def _read_section(definition_path: Path) -> dict[str, Any]:
    """Read and validate the simulation section of the document."""
    try:
        document = tomllib.loads(definition_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise BuildDefinitionError(f"'{definition_path}' is not valid TOML: {error}") from error
    section = document.get(SECTION)
    if not isinstance(section, dict):
        raise BuildDefinitionError(f"'{definition_path}' has no [{SECTION}] table")
    unknown = sorted(set(section) - KNOWN_KEYS)
    if unknown:
        raise BuildDefinitionError(f"Unknown keys in [{SECTION}]: {', '.join(unknown)}")
    return section


def _build(section: dict[str, Any], root: Path) -> SimulationBuildDefinition:
    """Translate the validated section into the domain object."""
    name = _required_text(section, "name")
    return SimulationBuildDefinition(
        name=name,
        header_directory=_required_path(section, "headers", root),
        generated_directory=_path(section, "generated", root) or root / DEFAULT_GENERATED_DIRECTORY,
        executable=_executable(section, root, name),
        source_directories=_paths(section, "sources", root),
        excluded_sources=_paths(section, "exclude", root),
        include_directories=_paths(section, "includes", root),
        definitions=_texts(section, "defines"),
        components=_texts(section, "components"),
        contract_path=_path(section, "contract", root),
        parse_include_directories=_paths(section, "parse_includes", root),
        parse_definitions=_texts(section, "parse_defines"),
        compiler=_text(section, "compiler"),
        language_standard=_text(section, "standard") or DEFAULT_LANGUAGE_STANDARD,
        warning_flags=_texts(section, "warnings") or DEFAULT_WARNING_FLAGS,
        record_calls=_flag(section, "record_calls", default=True),
        project_root=root,
        profile=_flag(section, "profile", default=False),
        track_allocations=_flag(section, "track_allocations", default=False),
        memory_budget=_count(section, "memory_budget"),
    )


def _executable(section: dict[str, Any], root: Path, name: str) -> Path:
    """Resolve the executable path, giving it the suffix the platform needs.

    A definition names ``build/blinky`` and gets ``build/blinky.exe`` on
    Windows, so that every later check looks at the file the linker actually
    wrote. An explicit suffix in the definition is left alone.
    """
    configured = _path(section, "executable", root)
    path = configured if configured is not None else root / DEFAULT_EXECUTABLE_DIRECTORY / name
    if path.suffix:
        return path
    return path.with_suffix(EXECUTABLE_SUFFIX)


def _text(section: dict[str, Any], key: str) -> str | None:
    """Read an optional string value."""
    value = section.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise BuildDefinitionError(f"[{SECTION}].{key} must be a string")
    return value


def _required_text(section: dict[str, Any], key: str) -> str:
    """Read a string value the definition cannot do without."""
    value = _text(section, key)
    if value is None:
        raise BuildDefinitionError(f"[{SECTION}] is missing the required key '{key}'")
    return value


def _texts(section: dict[str, Any], key: str) -> tuple[str, ...]:
    """Read an optional list of strings."""
    value = section.get(key, [])
    if not isinstance(value, list) or any(not isinstance(entry, str) for entry in value):
        raise BuildDefinitionError(f"[{SECTION}].{key} must be a list of strings")
    return tuple(value)


def _path(section: dict[str, Any], key: str, root: Path) -> Path | None:
    """Read an optional path, resolved against the definition directory."""
    value = _text(section, key)
    if value is None:
        return None
    return (root / value).resolve()


def _required_path(section: dict[str, Any], key: str, root: Path) -> Path:
    """Read a path the definition cannot do without."""
    return (root / _required_text(section, key)).resolve()


def _paths(section: dict[str, Any], key: str, root: Path) -> tuple[Path, ...]:
    """Read an optional list of paths, resolved against the definition."""
    return tuple((root / value).resolve() for value in _texts(section, key))


def _count(section: dict[str, Any], key: str) -> int:
    """Read an optional count, which is zero when it is not there."""
    value = section.get(key, 0)
    if not isinstance(value, int) or isinstance(value, bool) or (value < 0):
        raise BuildDefinitionError(f"[{SECTION}].{key} must be a count of zero or more")
    return value


def _flag(section: dict[str, Any], key: str, default: bool) -> bool:
    """Read an optional boolean value."""
    value = section.get(key, default)
    if not isinstance(value, bool):
        raise BuildDefinitionError(f"[{SECTION}].{key} must be true or false")
    return value
