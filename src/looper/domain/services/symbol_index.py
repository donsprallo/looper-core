"""Finding the function an address belongs to.

Two kinds of address arrive from a running simulation and they need
different answers. A profile reports where a function begins, which is
a name looked up exactly. An allocation reports where the call was
made from, which is somewhere in the middle of a function and is found
by taking the last function that begins at or before it.

The second is why this exists: an exact lookup of a return address
finds nothing, and a report full of hexadecimal is a report nobody
reads.
"""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Iterable
from dataclasses import dataclass, field

from looper.domain.model.firmware import FunctionSymbol


@dataclass(frozen=True)
class SymbolIndex:
    """Every function of a build, in address order.

    Attributes:
        symbols: The functions, sorted by where they begin.
    """

    symbols: tuple[FunctionSymbol, ...] = field(default_factory=tuple)

    @classmethod
    def of(cls, symbols: Iterable[FunctionSymbol]) -> SymbolIndex:
        """Build an index, putting the functions in address order."""
        return cls(tuple(sorted(symbols, key=lambda one: one.link_time_address)))

    @property
    def addresses(self) -> tuple[int, ...]:
        """Where each function begins, in order."""
        return tuple(one.link_time_address for one in self.symbols)

    def at(self, link_time_address: int) -> FunctionSymbol | None:
        """The function that begins exactly at an address."""
        found = self.containing(link_time_address)
        if (found is None) or (found.link_time_address != link_time_address):
            return None
        return found

    def containing(self, link_time_address: int) -> FunctionSymbol | None:
        """The function an address falls inside.

        The last one that begins at or before it, and only if the
        address really falls inside it. An address from outside the
        image -- a C runtime in a shared library, for instance --
        would otherwise be given the name of whatever function happens
        to come last, and a wrong name in a leak report is worse than
        no name at all.
        """
        if not self.symbols:
            return None
        position = bisect_right(self.addresses, link_time_address)
        if position == 0:
            return None
        found = self.symbols[position - 1]
        return found if found.contains(link_time_address) else None
