"""Use case that builds a simulation and starts it."""

from __future__ import annotations

from looper.application.commands.build_simulation import BuildSimulation
from looper.application.dto import BuildSimulationRequest, RunSimulationRequest
from looper.domain.ports import SimulationRunner

PORT_OPTION = "--port"
VIRTUAL_TIME_OPTION = "--virtual"


class RunSimulation:
    """Builds a simulation and runs it in the foreground.

    Building first is the default because a stale executable is the most
    expensive kind of confusion: it runs, it answers, and it is not the code
    being worked on.
    """

    def __init__(self, build: BuildSimulation, runner: SimulationRunner) -> None:
        self._build = build
        self._runner = runner

    def execute(self, request: RunSimulationRequest) -> int:
        """Build the simulation unless asked not to, then run it.

        Returns:
            The exit code of the simulation.

        Raises:
            SimulationBuildFailedError: If the compiler rejected the result.
            FileNotFoundError: If a skipped build leaves nothing to run.
        """
        build_request = BuildSimulationRequest(
            definition_path=request.definition_path,
            allow_incomplete_contract=request.allow_incomplete_contract,
        )
        definition = self._build.definition(build_request)
        if not request.skip_build:
            self._build.execute(build_request)
        elif not definition.executable.is_file():
            raise FileNotFoundError(f"Nothing built at '{definition.executable}'")
        return self._runner.run(definition.executable, _arguments(request))


def _arguments(request: RunSimulationRequest) -> tuple[str, ...]:
    """Translate the request into the arguments the simulation expects."""
    arguments: list[str] = []
    if request.port is not None:
        arguments.extend([PORT_OPTION, str(request.port)])
    if request.virtual_time:
        arguments.append(VIRTUAL_TIME_OPTION)
    return tuple(arguments)
