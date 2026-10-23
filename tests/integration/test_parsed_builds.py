"""Reading the debug information of one build only once.

The cost is lopsided: opening the container is milliseconds and
walking it the first time is a second and a half, because every
entry is decoded on the way past and kept. Three questions are
asked of one build, and asking each of them afresh is what made the
inspector's measurement tabs stand still for seconds at a time.

So what is checked here is that a second question is answered from
the first question's work, and -- which matters more -- that a
build replaced underneath a running client is read again rather
than answered from what it used to be.
"""

from __future__ import annotations

import time
from pathlib import Path

from looper.infrastructure.debug import DwarfDebugReader
from looper.infrastructure.debug.parsed_builds import BuildStamp, ParsedBuilds


def test_the_same_build_is_parsed_once(
    fixture_build: tuple[Path, tuple[int, int, int]],
) -> None:
    executable, _ = fixture_build
    parsed = ParsedBuilds()

    assert parsed.of(executable) is parsed.of(executable)


def test_the_same_file_under_another_name_is_the_same_build(
    fixture_build: tuple[Path, tuple[int, int, int]],
) -> None:
    """A path through the parent directory is not a second build."""
    executable, _ = fixture_build
    detoured = executable.parent / ".." / executable.parent.name / executable.name
    parsed = ParsedBuilds()

    assert parsed.of(executable) is parsed.of(detoured)


def test_a_rebuilt_executable_is_read_again(
    fixture_build: tuple[Path, tuple[int, int, int]], tmp_path: Path
) -> None:
    """A stale answer about a build that no longer exists is the worst one."""
    executable, _ = fixture_build
    copy = tmp_path / executable.name
    copy.write_bytes(executable.read_bytes())
    parsed = ParsedBuilds()
    first = parsed.of(copy)

    time.sleep(0.01)
    copy.write_bytes(executable.read_bytes())

    assert parsed.of(copy) is not first


def test_what_is_held_is_only_the_newest(
    fixture_build: tuple[Path, tuple[int, int, int]], tmp_path: Path
) -> None:
    """A client that rebuilds all afternoon would otherwise carry it all."""
    executable, _ = fixture_build
    copy = tmp_path / executable.name
    copy.write_bytes(executable.read_bytes())
    parsed = ParsedBuilds()
    parsed.of(copy)
    time.sleep(0.01)
    copy.write_bytes(executable.read_bytes())
    parsed.of(copy)

    assert len(parsed._parsed) == 1


def test_the_address_a_build_was_linked_against_is_read_once(
    fixture_build: tuple[Path, tuple[int, int, int]],
) -> None:
    """Asked once per reading by everything that gives an address a name."""
    executable, _ = fixture_build
    parsed = ParsedBuilds()

    first = parsed.base_of(executable)

    assert first > 0
    assert parsed.base_of(executable) == first


def test_a_rebuilt_executable_has_its_address_read_again(
    fixture_build: tuple[Path, tuple[int, int, int]], tmp_path: Path
) -> None:
    executable, _ = fixture_build
    copy = tmp_path / executable.name
    copy.write_bytes(executable.read_bytes())
    parsed = ParsedBuilds()
    parsed.base_of(copy)
    time.sleep(0.01)
    copy.write_bytes(executable.read_bytes())

    assert parsed.base_of(copy) == parsed.base_of(executable)


def test_forgetting_releases_it(fixture_build: tuple[Path, tuple[int, int, int]]) -> None:
    executable, _ = fixture_build
    parsed = ParsedBuilds()
    first = parsed.of(executable)

    parsed.forget()

    assert parsed.of(executable) is not first


def test_one_reader_answers_three_questions_from_one_read(
    fixture_build: tuple[Path, tuple[int, int, int]],
) -> None:
    """The three walks of one build share the entries each has decoded."""
    executable, _ = fixture_build
    reader = DwarfDebugReader()

    reader.read_variables(executable)
    started = time.perf_counter()
    functions = reader.read_functions(executable)
    statics = reader.read_statics(executable)
    spent = time.perf_counter() - started

    assert functions and statics
    assert spent < 1.0, f"the second and third questions took {spent:.2f} s"


def test_a_stamp_says_which_state_of_a_file_it_is(
    fixture_build: tuple[Path, tuple[int, int, int]],
) -> None:
    executable, _ = fixture_build
    stamp = BuildStamp.of(executable)

    assert stamp.path == executable.resolve()
    assert stamp.size == executable.stat().st_size
