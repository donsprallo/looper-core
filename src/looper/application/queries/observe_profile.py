"""Use case that reads where a whole simulation spends its time."""

from __future__ import annotations

from pathlib import Path

from looper.application.dto import ProfileView
from looper.application.errors import DebugInformationUnavailableError
from looper.application.mapping import build_profile_view
from looper.domain.model.firmware import FunctionSymbol, LoadedImage
from looper.domain.model.profile import MeasuredFunction, ProfiledFunction, ProfileReport
from looper.domain.model.sources import SourceLayout
from looper.domain.ports import DebugInformationReader, SimulationSession

#: Pages one reading will take before giving up. A profile longer than
#: this is longer than anything a client could usefully draw.
MAXIMUM_PAGES = 64


class ObserveProfile:
    """Reads the profile and gives every address back its name.

    The running process can only report addresses; the executable it was
    built from already describes which function sits at each of them and
    which file it was compiled from. Bringing the two together is the
    whole of this use case, and the reason the simulation carries no
    symbol table of its own.
    """

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

    def execute(self) -> ProfileView:
        """Read the profile and resolve it.

        Raises:
            DebugInformationUnavailableError: If the simulation did not
                report an executable, or that executable cannot be read.
        """
        executable = self._require_executable()
        symbols = self._symbols_of(executable)
        image = self._locate(executable)
        measurements, lost, is_profiling = self._read_all()
        report = ProfileReport(
            functions=tuple(self._resolve(one, symbols, image.slide) for one in measurements),
            lost_functions=lost,
        )
        return build_profile_view(report, is_profiling=is_profiling)

    def clear(self) -> None:
        """Forget the profile so that the next reading is its own window."""
        self._session.clear_profile()

    def _read_all(self) -> tuple[tuple[MeasuredFunction, ...], int, bool]:
        """Page through the profile until the position stops moving."""
        collected: list[MeasuredFunction] = []
        position = 0
        lost = 0
        is_profiling = False
        for _ in range(MAXIMUM_PAGES):
            page = self._session.read_profile(position)
            collected.extend(page.measurements)
            lost = page.lost
            is_profiling = is_profiling or page.is_profiling
            if page.next_position <= position:
                break
            position = page.next_position
        return tuple(collected), lost, is_profiling

    def _resolve(
        self,
        measured: MeasuredFunction,
        symbols: dict[int, FunctionSymbol],
        slide: int,
    ) -> ProfiledFunction:
        """Give one measurement the name and origin of what sits there."""
        symbol = symbols.get(measured.address - slide)
        source = symbol.source if symbol is not None else None
        return ProfiledFunction(
            name=symbol.name if symbol is not None else f"{measured.address:#x}",
            origin=self._layout.origin_of(source),
            source=source,
            calls=measured.calls,
            total_nanoseconds=measured.total_nanoseconds,
            self_nanoseconds=measured.self_nanoseconds,
            longest_nanoseconds=measured.longest_nanoseconds,
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
                "so the addresses in its profile cannot be given names."
            )
        return executable

    def _symbols_of(self, executable: Path) -> dict[int, FunctionSymbol]:
        """Every function the executable describes, by its entry address.

        Read once and kept. A firmware of any size holds a few thousand
        functions and parsing them takes a second or more, which is long
        enough to lengthen the very window being measured if it happened
        on every reading.

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

    def _locate(self, executable: Path) -> LoadedImage:
        """How far the process sits from its link time addresses.

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
