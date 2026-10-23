"""Firmware variable reader backed by the DWARF information of a build."""

from __future__ import annotations

import itertools
from collections.abc import Iterator
from pathlib import Path, PurePath

from elftools.dwarf.die import DIE
from elftools.dwarf.dwarfinfo import DWARFInfo

from looper.domain.model.firmware import (
    FirmwareVariable,
    FunctionSymbol,
    StaticSymbol,
    VariableOrigin,
)
from looper.domain.ports import DebugInformationReader
from looper.infrastructure.debug.dwarf_functions import read_functions
from looper.infrastructure.debug.dwarf_statics import read_statics
from looper.infrastructure.debug.dwarf_variables import (
    attributed_to,
    compiled_in,
    described_by,
    global_variables,
    name_of,
    simulation_units,
    static_address,
    type_of,
    within_tree,
)
from looper.infrastructure.debug.parsed_builds import ParsedBuilds
from looper.infrastructure.debug.scalar_expansion import ExpansionLimits, ScalarExpander

DEFAULT_MAXIMUM_VARIABLES = 50_000


class DwarfDebugReader(DebugInformationReader):
    """Lists the scalars a built simulation describes in its debug information.

    Only global variables are reported, which here means the ones declared at
    file scope. A local lives on a stack frame that exists while its function
    runs, so it has no address a watch could keep reading. A static inside a
    function does have one, but it is not a global and it is not named like
    one: two functions may each declare a ``counter``.

    Variables are walked into rather than listed whole, so what comes back are
    the scalars at the leaves of every structure and array. The limits on that
    walk are what keep a deeply nested configuration structure from expanding
    into more entries than a client can show.

    One reader keeps what it parsed, so the three questions asked of one build
    are one read rather than three; see `ParsedBuilds` for what that costs.
    A reader is therefore worth keeping for as long as the build is.
    """

    def __init__(
        self,
        limits: ExpansionLimits | None = None,
        maximum_variables: int = DEFAULT_MAXIMUM_VARIABLES,
    ) -> None:
        self._expander = ScalarExpander(limits)
        self._maximum_variables = maximum_variables
        self._simulation_units = simulation_units()
        self._parsed = ParsedBuilds()

    def read_link_time_base(self, executable: Path) -> int:
        """Read the base address the executable was linked against.

        Raises:
            FileNotFoundError: If the executable does not exist.
            DebugInformationError: If the container is not one we know.
        """
        self._require(executable)
        return self._parsed.base_of(executable)

    def read_variables(self, executable: Path) -> tuple[FirmwareVariable, ...]:
        """List every scalar inside a global variable the executable describes.

        Args:
            executable: Simulation built with debug information.

        Returns:
            The variables, in the order the compilation units declare them.

        Raises:
            FileNotFoundError: If the executable does not exist.
            DebugInformationError: If it carries no debug information.
        """
        self._require(executable)
        dwarf = self._parsed.of(executable)
        return tuple(itertools.islice(self._read(dwarf, executable), self._maximum_variables))

    def read_functions(self, executable: Path) -> tuple[FunctionSymbol, ...]:
        """List every function the executable places at an address.

        Args:
            executable: Simulation built with debug information.

        Returns:
            The functions, in the order the compilation units define them.

        Raises:
            FileNotFoundError: If the executable does not exist.
            DebugInformationError: If it carries no debug information.
        """
        self._require(executable)
        return read_functions(self._parsed.of(executable))

    def read_statics(self, executable: Path) -> tuple[StaticSymbol, ...]:
        """List every object the build holds statically, with its size.

        Args:
            executable: Simulation built with debug information.

        Returns:
            The objects, in the order the compilation units declare them.

        Raises:
            FileNotFoundError: If the executable does not exist.
            DebugInformationError: If it carries no debug information.
        """
        self._require(executable)
        return read_statics(self._parsed.of(executable))

    @staticmethod
    def _require(executable: Path) -> None:
        """Reject a path that is not a file before anything tries to parse it.

        Raises:
            FileNotFoundError: If the executable does not exist.
        """
        if not executable.is_file():
            raise FileNotFoundError(f"No simulation executable at {executable}")

    def _read(self, dwarf: DWARFInfo, executable: Path) -> Iterator[FirmwareVariable]:
        """Walk every compilation unit, reporting each variable once."""
        address_size = int(dwarf.config.default_address_size)
        tree = executable.resolve().parent
        seen: set[tuple[str, int]] = set()
        for unit in dwarf.iter_CUs():
            root = unit.get_top_DIE()
            source = name_of(root)
            origin = self._origin_of(source, compiled_in(root), tree)
            for die in global_variables(root):
                for variable in self._expand(die, address_size, source, origin):
                    key = (variable.path.text, variable.link_time_address)
                    if key not in seen:
                        seen.add(key)
                        yield variable

    def _expand(
        self, die: DIE, address_size: int, source: str | None, origin: VariableOrigin
    ) -> Iterator[FirmwareVariable]:
        """Expand one variable entry into the scalars it contains."""
        described = described_by(die)
        name = name_of(die) or name_of(described)
        address = static_address(die, address_size)
        if name is None or address is None:
            return
        type_die = type_of(die) or type_of(described)
        for variable in self._expander.expand(type_die, name, address):
            yield attributed_to(variable, source, origin)

    def _origin_of(self, source: str | None, compiled_in: str | None, tree: Path) -> VariableOrigin:
        """Decide which of the three programmes a compilation unit belongs to."""
        if source is not None and PurePath(source).name in self._simulation_units:
            return VariableOrigin.SIMULATION
        if compiled_in is not None and not within_tree(compiled_in, tree):
            return VariableOrigin.TOOLCHAIN
        return VariableOrigin.FIRMWARE
