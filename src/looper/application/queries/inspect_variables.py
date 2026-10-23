"""Use cases that read the firmware variables of a running simulation."""

from __future__ import annotations

from pathlib import Path

from looper.application.dto.variable_view import VariableView, WatchView
from looper.application.errors import DebugInformationUnavailableError
from looper.application.mapping.variable_view import build_variable_view, build_watch_view
from looper.domain.model.firmware import LoadedImage
from looper.domain.ports import DebugInformationReader, SimulationSession


class ListFirmwareVariables:
    """Reads the globals the running simulation was built with.

    Two sources have to be brought together, and only one of them can answer
    each half. The executable says which variables exist and what addresses
    they were linked at; the process says where it was actually loaded. The
    answer carries addresses that are already translated, so nothing further
    along has to know that a translation happened at all.

    Reading is not cheap -- a firmware of any size expands into thousands of
    scalars -- so a caller is expected to do it once and keep the result.
    """

    def __init__(self, session: SimulationSession, reader: DebugInformationReader) -> None:
        self._session = session
        self._reader = reader

    def execute(self) -> tuple[VariableView, ...]:
        """List every scalar inside a global of the running simulation.

        Returns:
            The variables, in the order the build declares them.

        Raises:
            DebugInformationUnavailableError: If the simulation did not report
                an executable, or that executable cannot be read.
        """
        executable = self._session.executable
        if executable is None:
            raise DebugInformationUnavailableError(
                "The simulation did not report which executable it is running, "
                "so its variables cannot be located."
            )
        image = self._locate(executable)
        try:
            variables = self._reader.read_variables(executable)
        except (OSError, ValueError) as error:
            raise DebugInformationUnavailableError(str(error)) from error
        return tuple(
            build_variable_view(variable, image.runtime_address_of(variable))
            for variable in variables
        )

    def _locate(self, executable: Path) -> LoadedImage:
        """Work out how far the process sits from its link time addresses.

        Raises:
            DebugInformationUnavailableError: If the executable cannot be read.
        """
        try:
            link_time_base = self._reader.read_link_time_base(executable)
        except (OSError, ValueError) as error:
            raise DebugInformationUnavailableError(str(error)) from error
        return LoadedImage(
            link_time_base=link_time_base,
            runtime_base=self._session.read_runtime_base(),
        )


class ObserveWatches:
    """Reads the variables the simulation is currently sampling."""

    def __init__(self, session: SimulationSession) -> None:
        self._session = session

    def execute(self) -> tuple[WatchView, ...]:
        """Take one snapshot of every watch and what it last read."""
        return tuple(build_watch_view(watch) for watch in self._session.read_variable_watches())
