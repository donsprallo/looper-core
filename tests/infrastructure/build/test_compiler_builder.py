"""A build as a hundred compiler runs instead of one, and fewer next time.

What matters is not that a compiler was invoked -- the integration
tests build a real example -- but what the builder does around it:
one command per unit, a link only if they all came back, every object
named so that two sources called the same thing cannot collide, a
running count of where it has got to, and nothing at all when nothing
changed.

No compiler runs here. The one call that would start one is replaced
by a stand-in that leaves the same files behind, because what the
next build decides is decided from those files.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from looper.domain.model.build import SimulationBuildDefinition
from looper.infrastructure.build import compiler_builder
from looper.infrastructure.build.compiler_builder import CompilerSimulationBuilder
from looper.infrastructure.build.compiler_invocation import (
    CompilerReply,
    compile_command,
    link_command,
)
from looper.infrastructure.build.translation_units import object_name, translation_units
from progress_doubles import RecordingProgress

COMPILE_ONLY = "-c"
OUTPUT_FLAG = "-o"
DEPENDENCY_FLAG = "-MF"
SOURCES = ("device_model.c", "board.c", "app.c")
HEADER = "board.h"

#: Far enough apart that no file system rounds two writes together.
A_SECOND = 1.0


class RecordingCompiler:
    """Stands in for the compiler: remembers, and leaves the files behind.

    The object, the dependency record and the executable are all
    written, because the next build reads exactly those to decide what
    it still has to do. Each is dated a second after what it was made
    from, so that the test does not depend on how finely the file
    system keeps time.
    """

    def __init__(self, rejects: str = "") -> None:
        self.commands: list[list[str]] = []
        self._rejects = rejects

    def __call__(self, command: list[str]) -> CompilerReply:
        self.commands.append(command)
        if self._rejects and any(self._rejects in part for part in command):
            return CompilerReply(succeeded=False, diagnostics=f"{self._rejects}: syntax error")
        self._produce(command)
        return CompilerReply(succeeded=True, diagnostics="")

    @property
    def compiles(self) -> list[list[str]]:
        """The commands that compiled one unit."""
        return [command for command in self.commands if COMPILE_ONLY in command]

    @property
    def links(self) -> list[list[str]]:
        """The commands that linked."""
        return [command for command in self.commands if COMPILE_ONLY not in command]

    def forget(self) -> None:
        """Start the next build with an empty record of commands."""
        self.commands = []

    def _produce(self, command: list[str]) -> None:
        """Write what this command was supposed to produce."""
        written = Path(command[command.index(OUTPUT_FLAG) + 1])
        if COMPILE_ONLY not in command:
            _write_after(written, [Path(one) for one in command if one.endswith(".o")])
            return
        source = Path(command[command.index(COMPILE_ONLY) + 1])
        _write_after(written, [source, *_headers_beside(source)])
        record = Path(command[command.index(DEPENDENCY_FLAG) + 1])
        listed = " ".join(str(one) for one in (source, *_headers_beside(source)))
        record.write_text(f"{written}: {listed}\n", encoding="utf-8")


def _headers_beside(source: Path) -> list[Path]:
    """The one header this little project has, when it is there."""
    header = source.with_name(HEADER)
    return [header] if header.is_file() else []


def _write_after(written: Path, made_from: list[Path]) -> None:
    """Write a file and date it a second after everything it came from."""
    written.parent.mkdir(parents=True, exist_ok=True)
    written.write_text("built", encoding="utf-8")
    latest = max((one.stat().st_mtime for one in made_from if one.is_file()), default=0.0)
    moment = max(latest + A_SECOND, written.stat().st_mtime)
    os.utime(written, (moment, moment))


@pytest.fixture
def definition(tmp_path: Path) -> SimulationBuildDefinition:
    """A project of three sources and one header they share."""
    sources = tmp_path / "src"
    sources.mkdir()
    for name in (*SOURCES, HEADER):
        (sources / name).write_text("/* content */\n", encoding="utf-8")
    (tmp_path / "generated").mkdir()
    return SimulationBuildDefinition(
        name="demo",
        header_directory=tmp_path / "Inc",
        generated_directory=tmp_path / "generated",
        executable=tmp_path / "build" / "demo",
        source_directories=(sources,),
        compiler="gcc",
    )


@pytest.fixture
def compiler(monkeypatch: pytest.MonkeyPatch) -> RecordingCompiler:
    """A compiler that agrees with everything, and remembers it."""
    recording = RecordingCompiler()
    _install(monkeypatch, recording)
    return recording


def _install(monkeypatch: pytest.MonkeyPatch, recording: RecordingCompiler) -> None:
    """Put the stand-in where the builder reaches for a compiler."""
    monkeypatch.setattr(compiler_builder, "run_compiler", recording)
    monkeypatch.setattr(
        CompilerSimulationBuilder, "_resolve_compiler", staticmethod(lambda _: "gcc")
    )


def test_every_source_is_compiled_on_its_own(
    definition: SimulationBuildDefinition, compiler: RecordingCompiler
) -> None:
    CompilerSimulationBuilder().build(definition)

    compiled = {
        Path(command[command.index(COMPILE_ONLY) + 1]).name for command in compiler.compiles
    }
    assert set(SOURCES) <= compiled


def test_the_objects_are_linked_once_at_the_end(
    definition: SimulationBuildDefinition, compiler: RecordingCompiler
) -> None:
    outcome = CompilerSimulationBuilder().build(definition)

    assert len(compiler.links) == 1
    assert str(definition.executable) in compiler.links[0]
    assert outcome.succeeded


def test_the_count_climbs_once_per_unit_and_ends_on_the_link(
    definition: SimulationBuildDefinition, compiler: RecordingCompiler
) -> None:
    progress = RecordingProgress()

    CompilerSimulationBuilder(progress).build(definition)

    units = len(compiler.compiles)
    assert [done for done, _, _ in progress.fractions] == [*range(1, units + 1), units]
    assert progress.fractions[-1][2].startswith("linking")


def test_a_second_build_that_has_nothing_to_do_does_nothing(
    definition: SimulationBuildDefinition, compiler: RecordingCompiler
) -> None:
    """Not even the link: the executable it would write is already there."""
    first = CompilerSimulationBuilder().build(definition)
    compiler.forget()

    outcome = CompilerSimulationBuilder().build(definition)

    assert compiler.commands == []
    assert outcome.succeeded
    assert outcome.recompiled_count == 0
    assert outcome.unit_count == first.unit_count


def test_a_changed_source_takes_its_own_unit_with_it(
    definition: SimulationBuildDefinition, compiler: RecordingCompiler
) -> None:
    CompilerSimulationBuilder().build(definition)
    compiler.forget()
    _rewrite(definition.source_directories[0] / "board.c")

    outcome = CompilerSimulationBuilder().build(definition)

    assert [_compiled_name(one) for one in compiler.compiles] == ["board.c"]
    assert len(compiler.links) == 1
    assert outcome.recompiled_count == 1


def test_a_changed_header_takes_everything_that_includes_it(
    definition: SimulationBuildDefinition, compiler: RecordingCompiler
) -> None:
    """Which is the only thing the dependency records are there for."""
    CompilerSimulationBuilder().build(definition)
    compiler.forget()
    _rewrite(definition.source_directories[0] / HEADER)

    CompilerSimulationBuilder().build(definition)

    assert sorted(_compiled_name(one) for one in compiler.compiles) == sorted(SOURCES)


def test_being_asked_to_rebuild_ignores_all_of_that(
    definition: SimulationBuildDefinition, compiler: RecordingCompiler
) -> None:
    first = CompilerSimulationBuilder().build(definition)
    compiler.forget()

    outcome = CompilerSimulationBuilder(rebuild=True).build(definition)

    assert outcome.recompiled_count == first.unit_count
    assert len(compiler.compiles) == first.unit_count


def test_a_unit_the_compiler_rejects_stops_the_build_before_the_link(
    definition: SimulationBuildDefinition, monkeypatch: pytest.MonkeyPatch
) -> None:
    recording = RecordingCompiler(rejects="board.c")
    _install(monkeypatch, recording)

    outcome = CompilerSimulationBuilder().build(definition)

    assert not outcome.succeeded
    assert "board.c: syntax error" in outcome.diagnostics
    assert recording.links == []


def test_a_unit_that_failed_is_compiled_again_next_time(
    definition: SimulationBuildDefinition, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Its object is the one from before, and must not look up to date."""
    rejecting = RecordingCompiler(rejects="board.c")
    _install(monkeypatch, rejecting)
    CompilerSimulationBuilder().build(definition)

    accepting = RecordingCompiler()
    _install(monkeypatch, accepting)
    CompilerSimulationBuilder().build(definition)

    assert "board.c" in [_compiled_name(one) for one in accepting.compiles]


def test_two_sources_of_the_same_name_get_different_objects() -> None:
    """Every module has a main.c, and they cannot share one object."""
    first = object_name(Path("app") / "main.c")
    second = object_name(Path("bsp") / "main.c")

    assert first != second
    assert first.startswith("main-")


def test_an_object_name_is_the_same_on_the_next_build() -> None:
    assert object_name(Path("app/main.c")) == object_name(Path("app/main.c"))


def test_a_compile_says_what_to_read_and_a_link_says_what_to_produce(
    definition: SimulationBuildDefinition,
) -> None:
    unit = translation_units(definition, ())[0]

    compiling = compile_command("gcc", definition, unit)
    linking = link_command("gcc", definition, (unit,))

    assert COMPILE_ONLY in compiling
    assert str(unit.dependencies) in compiling
    assert any(part.startswith("-I") for part in compiling)
    assert COMPILE_ONLY not in linking
    assert str(unit.object_file) in linking
    assert not any(part.startswith("-I") for part in linking)


def _compiled_name(command: list[str]) -> str:
    """The source one compile command was given."""
    return Path(command[command.index(COMPILE_ONLY) + 1]).name


def _rewrite(path: Path) -> None:
    """Change a file, and date it after whatever was built from it."""
    path.write_text("/* changed */\n", encoding="utf-8")
    moment = path.stat().st_mtime + A_SECOND * 10
    os.utime(path, (moment, moment))
