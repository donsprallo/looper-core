"""Use case that reads which way the time went, not only where.

The same bargain as the profile: the running process reports
addresses and the executable it was built from says which function
sits at each. What this adds is the shape -- each measurement
arrives with the node it was called from, and those hang back
together into the tree a flame graph is drawn from.

Following the paths costs the simulation something, so it is armed
while somebody is looking and idle otherwise. Arming begins a window
of its own, because what the calls did while nobody was following
them is of no use to whoever just asked.
"""

from __future__ import annotations

from pathlib import Path

from looper.application.dto.flame_view import FlameView
from looper.application.errors import DebugInformationUnavailableError
from looper.application.mapping.flame_view import build_flame_view
from looper.domain.model.firmware import FunctionSymbol
from looper.domain.model.profile import Flame, Frame, MeasuredPath
from looper.domain.model.sources import SourceLayout
from looper.domain.ports import DebugInformationReader, SimulationSession
from looper.domain.services import RecordedPath, build_flame

#: Pages one reading will take before giving up. A tree deeper than
#: this is deeper than anything a client could usefully draw.
MAXIMUM_PAGES = 64


class ObserveFlame:
    """Reads the tree of call paths and gives every address its name."""

    def __init__(
        self,
        session: SimulationSession,
        reader: DebugInformationReader,
        layout: SourceLayout | None = None,
    ) -> None:
        self._session = session
        self._reader = reader
        self._layout = layout if layout is not None else SourceLayout()
        self._symbols: dict[int, FunctionSymbol] | None = None
        self._watching = False

    @property
    def is_watching(self) -> bool:
        """Whether the simulation is following the calls for us."""
        return self._watching

    def watch(self, wanted: bool) -> None:
        """Ask the simulation to follow the calls, or to stop."""
        if wanted == self._watching:
            return
        self._session.watch_profile_paths(wanted)
        self._watching = wanted

    def execute(self) -> FlameView:
        """Read the tree and resolve it.

        Raises:
            DebugInformationUnavailableError: If the simulation did
                not report an executable, or it cannot be read.
        """
        executable = self._require_executable()
        symbols = self._symbols_of(executable)
        slide = self._session.read_runtime_base() - self._reader.read_link_time_base(executable)
        paths, lost, is_watched = self._read_all()
        return build_flame_view(
            Flame(
                roots=build_flame([self._resolve(one, symbols, slide) for one in paths]),
                lost_paths=lost,
                is_watched=is_watched,
            )
        )

    def _read_all(self) -> tuple[tuple[MeasuredPath, ...], int, bool]:
        """Page through the tree until the position stops moving."""
        collected: list[MeasuredPath] = []
        position = 0
        lost = 0
        is_watched = False
        for _ in range(MAXIMUM_PAGES):
            page = self._session.read_profile_paths(position)
            collected.extend(page.paths)
            lost = page.lost
            is_watched = is_watched or page.is_watched
            if page.next_position <= position:
                break
            position = page.next_position
        return tuple(collected), lost, is_watched

    def _resolve(
        self, path: MeasuredPath, symbols: dict[int, FunctionSymbol], slide: int
    ) -> RecordedPath:
        """Give one node the name and origin of what sits at its address."""
        symbol = symbols.get(path.address - slide)
        source = symbol.source if symbol is not None else None
        return RecordedPath(
            index=path.index,
            parent=path.parent,
            frame=Frame(
                name=symbol.name if symbol is not None else f"{path.address:#x}",
                origin=self._layout.origin_of(source),
                source=source,
                calls=path.calls,
                total_nanoseconds=path.total_nanoseconds,
                self_nanoseconds=path.self_nanoseconds,
            ),
        )

    def _require_executable(self) -> Path:
        """The executable the simulation is running.

        Raises:
            DebugInformationUnavailableError: If it did not name one.
        """
        executable = self._session.executable
        if executable is None:
            raise DebugInformationUnavailableError(
                "The simulation did not report which executable it is running, "
                "so the addresses in its call tree cannot be given names."
            )
        return executable

    def _symbols_of(self, executable: Path) -> dict[int, FunctionSymbol]:
        """Every function the executable describes, by its entry address.

        Read once and kept, for the same reason the profile keeps
        them: parsing a firmware takes long enough to lengthen the
        very window being measured.

        Raises:
            DebugInformationUnavailableError: If it cannot be read.
        """
        if self._symbols is not None:
            return self._symbols
        try:
            found = self._reader.read_functions(executable)
        except (OSError, ValueError) as error:
            raise DebugInformationUnavailableError(str(error)) from error
        self._symbols = {symbol.link_time_address: symbol for symbol in found}
        return self._symbols
