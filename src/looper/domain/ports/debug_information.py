"""The outbound interface to the debug information of a build."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from looper.domain.model.firmware.firmware_variable import FirmwareVariable
from looper.domain.model.firmware.function_symbol import FunctionSymbol
from looper.domain.model.firmware.static_symbol import StaticSymbol


class DebugInformationReader(ABC):
    """Reads what the debug information of a built simulation describes.

    Two things come from the same read, and have to: the variables and the
    base they are addressed against. Taking them from one parse of one file
    is what keeps them from describing different builds.
    """

    @abstractmethod
    def read_link_time_base(self, executable: Path) -> int:
        """Read the base address the executable was linked against.

        Args:
            executable: Simulation built with debug information.

        Returns:
            The base address, which is zero for a position independent
            executable.

        Raises:
            FileNotFoundError: If the executable does not exist.
            ValueError: If the container is not one the reader knows.
        """

    @abstractmethod
    def read_variables(self, executable: Path) -> tuple[FirmwareVariable, ...]:
        """List every scalar inside a global variable the executable describes.

        Structures and arrays are walked into, so what comes back are the
        scalars at the leaves rather than the aggregates on the way.

        Args:
            executable: Simulation built with debug information.

        Returns:
            The variables, in a stable order.

        Raises:
            FileNotFoundError: If the executable does not exist.
            ValueError: If it carries no debug information to read.
        """

    @abstractmethod
    def read_functions(self, executable: Path) -> tuple[FunctionSymbol, ...]:
        """List every function the executable describes, with its source.

        What a profile needs to say anything at all: an address alone is
        a number, and the source file is what sorts the firmware from
        the machinery around it.

        Args:
            executable: Simulation built with debug information.

        Returns:
            The functions, in a stable order.

        Raises:
            FileNotFoundError: If the executable does not exist.
            ValueError: If it carries no debug information to read.
        """

    @abstractmethod
    def read_statics(self, executable: Path) -> tuple[StaticSymbol, ...]:
        """List every object the build holds statically, with its size.

        What a simulation costs before it runs, which is the one kind
        of memory that can be described without running it.

        Args:
            executable: Simulation built with debug information.

        Returns:
            The objects, in the order the compilation units declare them.

        Raises:
            FileNotFoundError: If the executable does not exist.
            ValueError: If it carries no debug information to read.
        """
