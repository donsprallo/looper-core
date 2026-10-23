"""One function as the debug information describes it.

An address is all a running simulation can report about a function; a
name and a source file is what anyone reading the report needs. The
debug information already in the executable holds both, and this is the
pair it yields.

The source file is the one thing here that is not just decoration. It is
what says whether a function belongs to the firmware, to the device
model standing in for its board, or to the simulation's own machinery,
and no list anybody maintains has to agree with it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath


@dataclass(frozen=True)
class FunctionSymbol:
    """Where a function sits, what it is called, and where it came from.

    Attributes:
        name: Name the debug information gives it.
        link_time_address: Entry address, against the link time base.
        source: File it was compiled from, or ``None`` when the debug
            information names none.
        size_bytes: How far the function extends, or zero when the
            debug information does not say. It is what keeps an
            address from outside the image -- one in a shared library,
            say -- from being given the name of whatever happens to
            come last.
    """

    name: str
    link_time_address: int
    source: PurePath | None = None
    size_bytes: int = 0

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("A function symbol has a name")
        if self.link_time_address <= 0:
            raise ValueError(f"'{self.name}' has no usable entry address")
        if self.size_bytes < 0:
            raise ValueError(f"'{self.name}' cannot be {self.size_bytes} bytes long")

    def contains(self, link_time_address: int) -> bool:
        """Whether an address falls inside this function.

        A function whose length is unknown contains only its own first
        address: guessing an extent would put a name on something that
        is not there.
        """
        if link_time_address < self.link_time_address:
            return False
        return link_time_address < (self.link_time_address + max(self.size_bytes, 1))
