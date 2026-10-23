"""Whether something still has to be built.

Three questions, asked of the file system and of two small records
the last build left behind: has the source or any header it includes
changed, has the command changed, and is there an object at all. A
"no" to all three is the only reason to skip work, and anything that
cannot be answered counts as a yes.

That bias is the whole design. A build that recompiles something it
did not have to costs seconds; a build that skips something it should
have done produces an executable that runs, answers, and is not the
code being worked on -- which is the most expensive confusion there
is.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from looper.infrastructure.build.depfile import prerequisites
from looper.infrastructure.build.translation_units import TranslationUnit

NEWLINE = "\n"


def unit_is_fresh(unit: TranslationUnit, command: Sequence[str]) -> bool:
    """Whether this object can be kept instead of compiled again."""
    if not unit.object_file.is_file():
        return False
    if not command_unchanged(unit.command_record, command):
        return False
    needed = prerequisites(unit.dependencies)
    if not needed:
        return False
    return not _anything_newer(needed, unit.object_file)


def executable_is_fresh(
    executable: Path, units: Iterable[TranslationUnit], record: Path, command: Sequence[str]
) -> bool:
    """Whether the link can be skipped as well.

    The command names every object, so a unit added or taken away
    changes it and the link happens regardless of the timestamps.
    """
    if not executable.is_file():
        return False
    if not command_unchanged(record, command):
        return False
    return not _anything_newer((unit.object_file for unit in units), executable)


def command_unchanged(record: Path, command: Sequence[str]) -> bool:
    """Whether the last build ran this exact command."""
    try:
        return record.read_text(encoding="utf-8") == _written(command)
    except OSError:
        return False


def remember_command(record: Path, command: Sequence[str]) -> None:
    """Keep the command, now that it is known to have worked."""
    record.write_text(_written(command), encoding="utf-8")


def forget_command(record: Path) -> None:
    """Drop the record, so that whatever it described is built again.

    Called when the compiler refused: the object beside it is the one
    from before, and nothing about it should look up to date.
    """
    record.unlink(missing_ok=True)


def _anything_newer(prerequisites_of: Iterable[Path], target: Path) -> bool:
    """Whether any of these is missing, or as new as the target.

    As new rather than newer: a file system that keeps timestamps to
    the second can give a header and the object compiled from it the
    same one, and the cost of being wrong here is one recompile
    against a build that is quietly behind.
    """
    moment = target.stat().st_mtime_ns
    return any(_at_least_as_new(one, moment) for one in prerequisites_of)


def _at_least_as_new(prerequisite: Path, moment: int) -> bool:
    """Whether this file is missing, or was touched at or after then."""
    if not prerequisite.is_file():
        return True
    return prerequisite.stat().st_mtime_ns >= moment


def _written(command: Sequence[str]) -> str:
    """The command as it is kept on disk, one argument per line.

    A line per argument rather than one long line, because a person
    who opens the file to see why everything recompiled can read it.
    """
    return NEWLINE.join(command) + NEWLINE
