"""Keeping the debug information of a build, once it has been read.

Reading it is expensive and reading it again is nearly free, which
is an odd shape until you see where the cost sits. Opening the
container takes five milliseconds; walking it the first time takes
a second and a half, because every entry in it is decoded on the
way past and kept on the object doing the walking. Walk the same
object again and it costs fifty milliseconds.

So the object is what is worth keeping, not the answers. Three
questions are asked of one build -- which functions it has, what it
holds statically, which globals it declares -- and until now each
opened the file afresh and paid the second and a half again. An
inspector that reaches its Timing tab asks all three and stood
still for several seconds doing it.

What it costs to keep is about sixty megabytes for a two megabyte
executable, which is the same peak the walk reaches anyway. The
difference is only whether it is released afterwards, and for a
client that will ask again it should not be.

A build that is rebuilt under a running client is noticed: what
is held is kept under the file's size and the moment it was
written, so a new executable is read afresh and a stale one is
never answered from. Only the newest is held -- a client that
rebuilds all afternoon would otherwise be carrying every build of
the afternoon.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from elftools.dwarf.dwarfinfo import DWARFInfo

from looper.infrastructure.debug.debug_sections import open_dwarf_info, read_link_time_base


@dataclass(frozen=True)
class BuildStamp:
    """What tells one state of a built file from another.

    Attributes:
        path: Where it is, resolved, so that two names for one file
            are one entry.
        size: How large it is.
        written: When it was last written, in nanoseconds.
    """

    path: Path
    size: int
    written: int

    @classmethod
    def of(cls, executable: Path) -> BuildStamp:
        """Stamp one file as it is right now.

        Raises:
            FileNotFoundError: If there is no file there.
        """
        resolved = executable.resolve()
        status = resolved.stat()
        return cls(path=resolved, size=status.st_size, written=status.st_mtime_ns)


class ParsedBuilds:
    """What has been read of the build last asked about."""

    def __init__(self) -> None:
        self._parsed: dict[BuildStamp, DWARFInfo] = {}
        self._bases: dict[BuildStamp, int] = {}

    def of(self, executable: Path) -> DWARFInfo:
        """The debug information of one build, read once.

        Args:
            executable: Simulation built with debug information.

        Returns:
            The same object every time, so that what one walk
            decoded the next one does not decode again.

        Raises:
            FileNotFoundError: If the executable does not exist.
            DebugInformationError: If it carries none.
        """
        stamp = BuildStamp.of(executable)
        held = self._parsed.get(stamp)
        if held is not None:
            return held
        parsed = open_dwarf_info(executable)
        self._parsed = {stamp: parsed}
        return parsed

    def base_of(self, executable: Path) -> int:
        """The address one build was linked against, read once.

        A fixed property of a file, asked once per reading by
        everything that turns a running address back into a name.

        Args:
            executable: Simulation built with debug information.

        Returns:
            The link time base address.

        Raises:
            FileNotFoundError: If the executable does not exist.
            DebugInformationError: If the container is not one we know.
        """
        stamp = BuildStamp.of(executable)
        held = self._bases.get(stamp)
        if held is not None:
            return held
        base = read_link_time_base(executable)
        self._bases = {stamp: base}
        return base

    def forget(self) -> None:
        """Release what is held, for a client that is done asking."""
        self._parsed = {}
        self._bases = {}
