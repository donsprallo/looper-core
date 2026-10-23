"""Behaviour of the build use case.

What it produces, what it refuses, and what it says it is doing while
it works. Nothing here compiles anything; see the infrastructure
tests for the compiler driver and the integration tests for a build
that really happens.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from build_doubles import DEFINITION_PATH, StubBuilder, StubGenerate, a_build, a_definition

from looper.application.commands.build_simulation import BUILD_STEPS, COMPILING
from looper.application.commands.generate_simulation import GENERATION_STEPS
from looper.application.dto import BuildSimulationRequest
from looper.application.errors import SimulationBuildFailedError
from looper.application.progress import READING_DEFINITION
from progress_doubles import RecordingProgress

COMPILER = "gcc"


def a_request() -> BuildSimulationRequest:
    """The plainest build there is."""
    return BuildSimulationRequest(definition_path=DEFINITION_PATH)


def test_building_generates_into_the_directory_the_definition_names(tmp_path: Path) -> None:
    definition = a_definition(tmp_path)
    generate = StubGenerate()

    a_build(definition, generate=generate).execute(a_request())

    assert generate.requests[0].output_directory == definition.generated_directory
    assert generate.requests[0].header_directory == definition.header_directory


def test_a_successful_build_reports_the_executable_and_compiler(tmp_path: Path) -> None:
    definition = a_definition(tmp_path)

    report = a_build(definition).execute(a_request())

    assert report.executable == definition.executable
    assert report.compiler == COMPILER
    assert report.function_count == 5


def test_a_rejected_build_names_the_compiler_and_its_output(tmp_path: Path) -> None:
    use_case = a_build(a_definition(tmp_path), builder=StubBuilder(succeeded=False))

    with pytest.raises(SimulationBuildFailedError, match="undefined reference"):
        use_case.execute(a_request())


def test_the_published_plan_is_the_build_around_the_generation() -> None:
    """One tuple, so the bar cannot count steps the build does not take."""
    assert (READING_DEFINITION, *GENERATION_STEPS, COMPILING) == BUILD_STEPS


def test_a_build_announces_its_own_two_steps(tmp_path: Path) -> None:
    """The four between them belong to generation, which says them itself."""
    progress = RecordingProgress()

    a_build(a_definition(tmp_path), progress=progress).execute(a_request())

    assert progress.announced == [READING_DEFINITION, COMPILING]
    assert progress.summaries == ["demo", "demo"]
    assert progress.open_steps == 0


def test_a_rejected_build_leaves_the_compiler_step_open(tmp_path: Path) -> None:
    progress = RecordingProgress()
    use_case = a_build(
        a_definition(tmp_path), builder=StubBuilder(succeeded=False), progress=progress
    )

    with pytest.raises(SimulationBuildFailedError):
        use_case.execute(a_request())

    assert progress.announced[-1] == COMPILING
    assert progress.open_steps == 1


def test_a_build_that_compiled_everything_says_how_much_that_was(tmp_path: Path) -> None:
    """The number is the whole reason the step took as long as it did."""
    progress = RecordingProgress()
    builder = StubBuilder(unit_count=143, recompiled_count=143)

    a_build(a_definition(tmp_path), builder=builder, progress=progress).execute(a_request())

    assert progress.summaries[-1] == "demo, 143 units"


def test_a_build_that_compiled_some_of_them_says_which_share(tmp_path: Path) -> None:
    progress = RecordingProgress()
    builder = StubBuilder(unit_count=143, recompiled_count=7)

    a_build(a_definition(tmp_path), builder=builder, progress=progress).execute(a_request())

    assert progress.summaries[-1] == "demo, 7 of 143 units"


def test_a_build_with_nothing_to_do_says_that_too(tmp_path: Path) -> None:
    """Otherwise a build that took no time looks like one that failed."""
    progress = RecordingProgress()
    builder = StubBuilder(unit_count=143)

    a_build(a_definition(tmp_path), builder=builder, progress=progress).execute(a_request())

    assert progress.summaries[-1] == "demo, 143 units unchanged"
