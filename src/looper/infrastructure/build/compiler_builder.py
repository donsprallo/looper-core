"""Simulation builder that drives a C compiler directly.

One compiler run per translation unit, then one link, and neither of
them if nothing changed. The alternative -- a single invocation over
every source -- is a shorter command line and a longer silence: it
says nothing for as long as it takes, it uses one core to do a
hundred and forty files, and it does all of them every time.

What makes skipping safe is that the compiler is asked to write down
what each unit was built from, headers included, and what it was
asked to do. See `freshness`, which is deliberately eager to rebuild.
"""

from __future__ import annotations

import os
import shutil
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path

from looper.domain.model.build import BuildOutcome, SimulationBuildDefinition
from looper.domain.ports import ProgressListener, SilentProgress, SimulationBuilder
from looper.infrastructure.build.compiler_invocation import (
    CompilerReply,
    compile_command,
    link_command,
    run_compiler,
)
from looper.infrastructure.build.errors import MissingCompilerError
from looper.infrastructure.build.freshness import (
    executable_is_fresh,
    forget_command,
    remember_command,
    unit_is_fresh,
)
from looper.infrastructure.build.project_sources import runtime_units
from looper.infrastructure.build.translation_units import (
    TranslationUnit,
    link_record,
    objects_directory,
    translation_units,
)

CANDIDATE_COMPILERS = ("gcc", "clang", "cc")
MISSING_COMPILER_MESSAGE = (
    "No C compiler found. Install gcc or clang, or name one in the build "
    'definition with: compiler = "..."'
)

#: What the live display is told while the objects are being linked.
LINKING = "linking"

NEWLINE = "\n"

#: Every unit of a build and the command that compiles it.
Plan = dict[TranslationUnit, list[str]]


class CompilerSimulationBuilder(SimulationBuilder):
    """Compiles the generated sources, the runtime and the firmware.

    A compiler driven directly rather than a generated build system: a
    simulation has no configuration to discover, and a command that can
    be copied out of an error message and run by hand is worth more
    here than a build tree.
    """

    def __init__(self, progress: ProgressListener | None = None, rebuild: bool = False) -> None:
        self._progress = progress if progress is not None else SilentProgress()
        self._rebuild = rebuild

    def build(self, definition: SimulationBuildDefinition) -> BuildOutcome:
        """Compile whatever is out of date, and link if anything was.

        Raises:
            MissingCompilerError: If no usable compiler can be found.
        """
        compiler = self._resolve_compiler(definition.compiler)
        definition.executable.parent.mkdir(parents=True, exist_ok=True)
        objects_directory(definition).mkdir(parents=True, exist_ok=True)
        planned = self._plan(compiler, definition)
        stale = self._out_of_date(planned)
        compiled = self._compile_all(stale, planned)
        if not all(reply.succeeded for reply in compiled):
            return _outcome(definition, compiler, compiled, planned, stale)
        linked = self._link(compiler, definition, tuple(planned))
        return _outcome(definition, compiler, (*compiled, *linked), planned, stale)

    def _plan(self, compiler: str, definition: SimulationBuildDefinition) -> Plan:
        """Every unit of this build and the command that compiles it."""
        units = translation_units(definition, runtime_units(definition.track_allocations))
        return {unit: compile_command(compiler, definition, unit) for unit in units}

    def _out_of_date(self, planned: Plan) -> tuple[TranslationUnit, ...]:
        """The units that have to be compiled again."""
        if self._rebuild:
            return tuple(planned)
        return tuple(unit for unit, command in planned.items() if not unit_is_fresh(unit, command))

    def _compile_all(
        self, stale: tuple[TranslationUnit, ...], planned: Plan
    ) -> tuple[CompilerReply, ...]:
        """Compile every stale unit, as many at a time as there are cores.

        The replies come back in the order the units were listed,
        whatever order they finished in, so that the diagnostics of a
        failed build read the same way twice.
        """
        if not stale:
            return ()
        with ThreadPoolExecutor(max_workers=_worker_count()) as pool:
            started = {pool.submit(_compile, unit, planned[unit]): unit for unit in stale}
            self._watch(started)
        return tuple(one.result() for one in started)

    def _watch(self, started: dict[Future[CompilerReply], TranslationUnit]) -> None:
        """Say how many units are done as each one finishes."""
        for done, finished in enumerate(as_completed(started), start=1):
            self._progress.advance(done, len(started), started[finished].source.name)

    def _link(
        self,
        compiler: str,
        definition: SimulationBuildDefinition,
        units: tuple[TranslationUnit, ...],
    ) -> tuple[CompilerReply, ...]:
        """Put the objects together, unless the executable already is.

        Nothing at all is the normal outcome of building twice, and
        saying so is better than relinking a hundred objects to
        produce the file that is already there.
        """
        command = link_command(compiler, definition, units)
        record = link_record(definition)
        if executable_is_fresh(definition.executable, units, record, command):
            return ()
        self._progress.advance(len(units), len(units), f"{LINKING} {definition.executable.name}")
        reply = run_compiler(command)
        _keep_or_drop(record, command, reply)
        return (reply,)

    @staticmethod
    def _resolve_compiler(requested: str | None) -> str:
        """Find the compiler to invoke.

        Raises:
            MissingCompilerError: If none is available.
        """
        candidates = (requested,) if requested else CANDIDATE_COMPILERS
        for candidate in candidates:
            found = shutil.which(candidate) if candidate else None
            if found is not None:
                return found
        if requested:
            raise MissingCompilerError(f"The compiler '{requested}' is not on PATH")
        raise MissingCompilerError(MISSING_COMPILER_MESSAGE)


def _compile(unit: TranslationUnit, command: list[str]) -> CompilerReply:
    """Compile one unit, and record what built it if it worked."""
    reply = run_compiler(command)
    _keep_or_drop(unit.command_record, command, reply)
    return reply


def _keep_or_drop(record: Path, command: list[str], reply: CompilerReply) -> None:
    """Keep the command when it worked, and drop it when it did not.

    A command kept after a failure would describe an object that was
    never written, and the next build would believe it.
    """
    if reply.succeeded:
        remember_command(record, command)
        return
    forget_command(record)


def _outcome(
    definition: SimulationBuildDefinition,
    compiler: str,
    replies: tuple[CompilerReply, ...],
    planned: Plan,
    stale: tuple[TranslationUnit, ...],
) -> BuildOutcome:
    """What the whole build came to.

    Every reply is kept, warnings from units that succeeded included,
    because that is what one invocation over every source used to hand
    back and it is what a reader of a failed build wants.
    """
    return BuildOutcome(
        executable=definition.executable,
        succeeded=all(reply.succeeded for reply in replies),
        compiler=compiler,
        diagnostics=NEWLINE.join(reply.diagnostics for reply in replies if reply.diagnostics),
        unit_count=len(planned),
        recompiled_count=len(stale),
    )


def _worker_count() -> int:
    """How many compilers to run at once."""
    return max(1, os.cpu_count() or 1)
