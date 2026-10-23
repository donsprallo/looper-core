"""When a unit may be kept, and when it has to be built again.

Every case here is a way of being wrong in one of two directions.
Rebuilding something that did not need it costs a second. Keeping
something that did produces an executable that runs, answers, and is
not the code being worked on, so everything unknown counts as stale.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from looper.infrastructure.build.freshness import (
    executable_is_fresh,
    forget_command,
    remember_command,
    unit_is_fresh,
)
from looper.infrastructure.build.translation_units import TranslationUnit

COMMAND = ["gcc", "-c", "app.c", "-o", "app.o"]
OTHER_COMMAND = ["gcc", "-O2", "-c", "app.c", "-o", "app.o"]

#: Far enough apart that no file system rounds the two together.
A_SECOND_LATER = 1.0


def touch(path: Path, at: float | None = None) -> Path:
    """Write a file, optionally dated."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")
    if at is not None:
        os.utime(path, (at, at))
    return path


@pytest.fixture
def unit(tmp_path: Path) -> TranslationUnit:
    """A unit that was compiled, with everything its build left behind."""
    source = touch(tmp_path / "src" / "app.c")
    header = touch(tmp_path / "src" / "app.h")
    one = TranslationUnit(source=source, object_file=tmp_path / "objects" / "app.o")
    touch(one.object_file, at=_moment(source) + A_SECOND_LATER)
    one.dependencies.write_text(f"{one.object_file}: {source} {header}\n", encoding="utf-8")
    remember_command(one.command_record, COMMAND)
    return one


def _moment(path: Path) -> float:
    """When a file was last written."""
    return path.stat().st_mtime


def test_a_unit_nothing_has_touched_is_kept(unit: TranslationUnit) -> None:
    assert unit_is_fresh(unit, COMMAND)


def test_a_unit_whose_source_changed_is_built_again(unit: TranslationUnit) -> None:
    touch(unit.source, at=_moment(unit.object_file) + A_SECOND_LATER)

    assert not unit_is_fresh(unit, COMMAND)


def test_a_unit_whose_header_changed_is_built_again(unit: TranslationUnit) -> None:
    """The whole reason the compiler is asked to write the list."""
    touch(unit.source.with_name("app.h"), at=_moment(unit.object_file) + A_SECOND_LATER)

    assert not unit_is_fresh(unit, COMMAND)


def test_a_header_that_was_deleted_is_built_again(unit: TranslationUnit) -> None:
    unit.source.with_name("app.h").unlink()

    assert not unit_is_fresh(unit, COMMAND)


def test_a_unit_compiled_with_other_flags_is_built_again(unit: TranslationUnit) -> None:
    assert not unit_is_fresh(unit, OTHER_COMMAND)


def test_a_unit_with_no_object_is_built(unit: TranslationUnit) -> None:
    unit.object_file.unlink()

    assert not unit_is_fresh(unit, COMMAND)


def test_a_unit_with_no_dependency_record_is_built(unit: TranslationUnit) -> None:
    """Not knowing what it depends on is not the same as depending on nothing."""
    unit.dependencies.unlink()

    assert not unit_is_fresh(unit, COMMAND)


def test_a_unit_whose_command_was_forgotten_is_built(unit: TranslationUnit) -> None:
    """What the builder does when the compiler refused."""
    forget_command(unit.command_record)

    assert not unit_is_fresh(unit, COMMAND)


def test_forgetting_a_command_that_was_never_kept_is_allowed(tmp_path: Path) -> None:
    forget_command(tmp_path / "nothing.cmd")


def test_an_executable_newer_than_every_object_is_kept(
    tmp_path: Path, unit: TranslationUnit
) -> None:
    executable = touch(tmp_path / "demo.exe", at=_moment(unit.object_file) + A_SECOND_LATER)
    record = tmp_path / "link.cmd"
    remember_command(record, COMMAND)

    assert executable_is_fresh(executable, (unit,), record, COMMAND)


def test_an_executable_older_than_an_object_is_linked_again(
    tmp_path: Path, unit: TranslationUnit
) -> None:
    executable = touch(tmp_path / "demo.exe", at=_moment(unit.object_file) - A_SECOND_LATER)
    record = tmp_path / "link.cmd"
    remember_command(record, COMMAND)

    assert not executable_is_fresh(executable, (unit,), record, COMMAND)


def test_a_different_link_command_is_linked_again(tmp_path: Path, unit: TranslationUnit) -> None:
    """Which is how a unit added or taken away reaches the link."""
    executable = touch(tmp_path / "demo.exe", at=_moment(unit.object_file) + A_SECOND_LATER)
    record = tmp_path / "link.cmd"
    remember_command(record, COMMAND)

    assert not executable_is_fresh(executable, (unit,), record, OTHER_COMMAND)


def test_an_executable_that_is_not_there_is_linked(tmp_path: Path, unit: TranslationUnit) -> None:
    record = tmp_path / "link.cmd"
    remember_command(record, COMMAND)

    assert not executable_is_fresh(tmp_path / "gone.exe", (unit,), record, COMMAND)
