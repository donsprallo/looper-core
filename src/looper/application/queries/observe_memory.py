"""Use case that reports where a simulation's memory goes."""

from __future__ import annotations

from pathlib import Path

from looper.application.dto import MemoryView
from looper.application.errors import DebugInformationUnavailableError
from looper.application.mapping import build_memory_view
from looper.domain.model.firmware import LoadedImage
from looper.domain.model.memory import (
    AllocationSite,
    HeapReading,
    HeapUsage,
    MeasuredSite,
    StackFrame,
    StackUsage,
    StaticMemoryReport,
)
from looper.domain.model.profile import ProfileReading
from looper.domain.model.sources import SourceLayout
from looper.domain.ports import DebugInformationReader, SimulationSession
from looper.domain.services import SymbolIndex, describe_static_memory


class ObserveMemory:
    """Reads the three places a simulation's memory goes.

    Statically, before it runs; on the stack, as deep as it went; and
    on the heap, as much as it asked for. Three measurements by three
    means, and all three arrive as addresses until the executable's
    own debug information gives them names.

    What is read once and kept is everything that cannot change while
    the simulation runs: the objects it holds statically and where each
    function begins. Parsing those on every reading would take longer
    than the window being measured.
    """

    def __init__(
        self,
        session: SimulationSession,
        reader: DebugInformationReader,
        layout: SourceLayout | None = None,
        budget_bytes: int = 0,
    ) -> None:
        self._session = session
        self._reader = reader
        self._layout = layout if layout is not None else SourceLayout()
        self._budget_bytes = budget_bytes
        self._index: SymbolIndex | None = None
        self._static: StaticMemoryReport | None = None

    def execute(self) -> MemoryView:
        """Read all three and give every address a name.

        Raises:
            DebugInformationUnavailableError: If the simulation did not
                report an executable, or that executable cannot be read.
        """
        executable = self._require_executable()
        index = self._index_of(executable)
        slide = self._locate(executable).slide
        return build_memory_view(
            static=self._static_memory(executable),
            stack=self._stack_usage(self._session.read_profile(0), index, slide),
            heap=self._heap_usage(self._session.read_heap(), index, slide),
        )

    def clear(self) -> None:
        """Begin a new window for both of the measured parts."""
        self._session.clear_profile()
        self._session.clear_heap()

    def _stack_usage(self, reading: ProfileReading, index: SymbolIndex, slide: int) -> StackUsage:
        """Describe how deep the stack went and what was on it.

        The path arrives as bare addresses; what each of those frames
        cost was measured separately, per function, so the two are
        joined here rather than reported apart.
        """
        measured = {one.address: one.frame_bytes for one in reading.measurements}
        return StackUsage(
            deepest_bytes=reading.deepest_stack_bytes,
            deepest_depth=reading.deepest_depth,
            path=tuple(
                self._frame(address, measured.get(address, 0), index, slide)
                for address in reading.stack_path
            ),
            frames=tuple(
                self._frame(one.address, one.frame_bytes, index, slide)
                for one in reading.measurements
                if one.frame_bytes > 0
            ),
            path_is_complete=reading.stack_path_is_complete,
        )

    def _frame(self, address: int, bytes_used: int, index: SymbolIndex, slide: int) -> StackFrame:
        """One function on the stack, named if anything names it."""
        symbol = index.at(address - slide)
        source = symbol.source if symbol is not None else None
        return StackFrame(
            function=symbol.name if symbol is not None else f"{address:#x}",
            origin=self._layout.origin_of(source),
            source=source,
            bytes_used=bytes_used,
        )

    def _heap_usage(self, reading: HeapReading, index: SymbolIndex, slide: int) -> HeapUsage:
        """Describe what the allocator was asked for."""
        return HeapUsage(
            allocations=reading.allocations,
            frees=reading.frees,
            failures=reading.failures,
            live_bytes=reading.live_bytes,
            peak_bytes=reading.peak_bytes,
            outstanding=tuple(self._site(one, index, slide) for one in reading.outstanding),
            untracked_blocks=reading.untracked_blocks,
            is_watched=reading.is_watched,
        )

    def _site(self, measured: MeasuredSite, index: SymbolIndex, slide: int) -> AllocationSite:
        """One place that allocated, named if anything names it.

        An allocation reports where the call was made from, which is
        inside a function rather than at its beginning, so this asks
        which function the address falls in rather than which one
        begins there.
        """
        symbol = index.containing(measured.address - slide)
        source = symbol.source if symbol is not None else None
        return AllocationSite(
            function=symbol.name if symbol is not None else f"{measured.address:#x}",
            origin=self._layout.origin_of(source),
            source=source,
            blocks=measured.blocks,
            bytes_used=measured.bytes_used,
        )

    def _static_memory(self, executable: Path) -> StaticMemoryReport:
        """What the build holds statically, read once and kept.

        Raises:
            DebugInformationUnavailableError: If it cannot be read.
        """
        if self._static is not None:
            return self._static
        try:
            symbols = self._reader.read_statics(executable)
        except (OSError, ValueError) as error:
            raise DebugInformationUnavailableError(str(error)) from error
        self._static = describe_static_memory(symbols, self._layout, self._budget_bytes)
        return self._static

    def _require_executable(self) -> Path:
        """The executable the simulation is running.

        Raises:
            DebugInformationUnavailableError: If it did not name one.
        """
        executable = self._session.executable
        if executable is None:
            raise DebugInformationUnavailableError(
                "The simulation did not report which executable it is running, "
                "so what it holds in memory cannot be described."
            )
        return executable

    def _index_of(self, executable: Path) -> SymbolIndex:
        """Every function of the build, in address order, read once.

        Raises:
            DebugInformationUnavailableError: If it cannot be read.
        """
        if self._index is not None:
            return self._index
        try:
            found = self._reader.read_functions(executable)
        except (OSError, ValueError) as error:
            raise DebugInformationUnavailableError(str(error)) from error
        self._index = SymbolIndex.of(found)
        return self._index

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
