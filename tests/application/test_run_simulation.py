"""Behaviour of the run use case.

It builds and then starts what came out. What is worth pinning down
is the part a script depends on: that the build happens first unless
it was told not to, and that the exit code is the simulation's own.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from build_doubles import DEFINITION_PATH, RecordingRunner, StubBuilder, a_build, a_definition

from looper.application.commands import RunSimulation
from looper.application.dto import RunSimulationRequest


def test_running_builds_first_by_default(tmp_path: Path) -> None:
    builder = StubBuilder()
    runner = RecordingRunner()
    definition = a_definition(tmp_path)

    RunSimulation(a_build(definition, builder=builder), runner).execute(
        RunSimulationRequest(definition_path=DEFINITION_PATH)
    )

    assert builder.calls == 1
    assert runner.started == definition.executable


def test_the_simulation_exit_code_is_handed_back(tmp_path: Path) -> None:
    runner = RecordingRunner(exit_code=3)

    code = RunSimulation(a_build(a_definition(tmp_path)), runner).execute(
        RunSimulationRequest(definition_path=DEFINITION_PATH)
    )

    assert code == 3


def test_port_and_clock_reach_the_simulation(tmp_path: Path) -> None:
    runner = RecordingRunner()

    RunSimulation(a_build(a_definition(tmp_path)), runner).execute(
        RunSimulationRequest(definition_path=DEFINITION_PATH, port=45771, virtual_time=True)
    )

    assert runner.arguments == ("--port", "45771", "--virtual")


def test_skipping_the_build_requires_something_to_run(tmp_path: Path) -> None:
    builder = StubBuilder()
    use_case = RunSimulation(a_build(a_definition(tmp_path), builder=builder), RecordingRunner())

    with pytest.raises(FileNotFoundError, match="Nothing built"):
        use_case.execute(RunSimulationRequest(definition_path=DEFINITION_PATH, skip_build=True))
    assert builder.calls == 0


def test_an_existing_executable_may_be_started_unchanged(tmp_path: Path) -> None:
    executable = tmp_path / "demo.bin"
    executable.write_bytes(b"")
    builder = StubBuilder()
    runner = RecordingRunner()

    RunSimulation(a_build(a_definition(tmp_path, executable), builder=builder), runner).execute(
        RunSimulationRequest(definition_path=DEFINITION_PATH, skip_build=True)
    )

    assert builder.calls == 0
    assert runner.started == executable
