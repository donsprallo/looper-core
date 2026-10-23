"""Writing the generated sources, and not writing them again.

Generation runs before every build and usually produces exactly the
adapter it produced last time. Writing that out regardless would give
every generated file a new timestamp, and the hooks header is
included by most of the simulation -- so a build that had nothing to
do would compile almost all of it.
"""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path, PurePosixPath

import pytest

from looper.domain.model.codegen import ArtifactKind, GeneratedArtifact
from looper.infrastructure.filesystem import FileSystemArtifactRepository

CONTENT = "/* generated */\n"
ARTIFACT = GeneratedArtifact(
    relative_path=PurePosixPath("sil_adapter_demo.c"),
    kind=ArtifactKind.C_SOURCE,
    content=CONTENT,
)

#: Far enough back that no file system rounds the two together.
A_SECOND_AGO = 1.0


def test_an_artifact_is_written_where_it_belongs(tmp_path: Path) -> None:
    FileSystemArtifactRepository().write_all(tmp_path, [ARTIFACT])

    assert (tmp_path / "sil_adapter_demo.c").read_text(encoding="utf-8") == CONTENT


def test_intermediate_directories_are_made(tmp_path: Path) -> None:
    nested = replace(ARTIFACT, relative_path=PurePosixPath("deep/down/one.c"))

    FileSystemArtifactRepository().write_all(tmp_path, [nested])

    assert (tmp_path / "deep" / "down" / "one.c").is_file()


def test_a_file_that_already_says_this_is_left_alone(tmp_path: Path) -> None:
    """Untouched timestamp and all: a build decides from timestamps."""
    repository = FileSystemArtifactRepository()
    repository.write_all(tmp_path, [ARTIFACT])
    written = tmp_path / "sil_adapter_demo.c"
    earlier = written.stat().st_mtime - A_SECOND_AGO
    os.utime(written, (earlier, earlier))

    repository.write_all(tmp_path, [ARTIFACT])

    assert written.stat().st_mtime == pytest.approx(earlier)


def test_a_file_that_says_something_else_is_written(tmp_path: Path) -> None:
    repository = FileSystemArtifactRepository()
    repository.write_all(tmp_path, [ARTIFACT])
    written = tmp_path / "sil_adapter_demo.c"
    earlier = written.stat().st_mtime - A_SECOND_AGO
    os.utime(written, (earlier, earlier))

    repository.write_all(tmp_path, [replace(ARTIFACT, content="/* other */\n")])

    assert written.read_text(encoding="utf-8") == "/* other */\n"
    assert written.stat().st_mtime > earlier
