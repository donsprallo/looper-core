"""Reading what a compiler said an object was built from.

The format is a makefile rule and every awkward part of it is a way
of being wrong quietly: a path that is misread is a file that does
not exist, which makes a unit look out of date for ever, and a target
mistaken for a prerequisite would make it look out of date too.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from looper.infrastructure.build.depfile import prerequisites

SIMPLE = "app.o: app.c app.h\n"
CONTINUED = "app.o: app.c \\\n  one.h \\\n  two.h\n"
WINDOWS = "C:/build/app.o: C:/src/app.c C:/src/app.h\n"
SPACED = "app.o: /home/me/My\\ Project/app.c\n"


def written(tmp_path: Path, text: str) -> Path:
    """One dependency file, as a compiler would have left it."""
    record = tmp_path / "app.d"
    record.write_text(text, encoding="utf-8")
    return record


def names(found: tuple[Path, ...]) -> list[str]:
    """What was read, by file name."""
    return [one.name for one in found]


def test_the_source_and_its_headers_are_read(tmp_path: Path) -> None:
    assert names(prerequisites(written(tmp_path, SIMPLE))) == ["app.c", "app.h"]


def test_a_rule_continued_over_several_lines_is_one_list(tmp_path: Path) -> None:
    assert names(prerequisites(written(tmp_path, CONTINUED))) == ["app.c", "one.h", "two.h"]


def test_the_drive_letter_of_a_windows_path_is_not_the_target(tmp_path: Path) -> None:
    """Both the target and its prerequisites begin with a colon here."""
    assert names(prerequisites(written(tmp_path, WINDOWS))) == ["app.c", "app.h"]


def test_a_space_inside_a_path_does_not_split_it(tmp_path: Path) -> None:
    found = prerequisites(written(tmp_path, SPACED))

    assert len(found) == 1
    assert found[0].name == "app.c"
    assert "My Project" in found[0].parts


def test_no_record_is_not_the_same_as_no_dependencies(tmp_path: Path) -> None:
    """A caller reads nothing as "do not know", which means rebuild."""
    assert prerequisites(tmp_path / "never-written.d") == ()


@pytest.mark.parametrize("text", ["", "\n", "no-colon-here at all\n"])
def test_a_record_that_says_nothing_usable_reads_as_nothing(tmp_path: Path, text: str) -> None:
    assert prerequisites(written(tmp_path, text)) == ()
