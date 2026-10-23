"""One statically allocated object as the debug information describes it.

The counterpart of `FunctionSymbol`: where that says what sits at an
address, this says how much room something takes and where it was
declared. Both come from the same read of the same file, and both are
what turns a measurement into something a person can act on.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath


@dataclass(frozen=True)
class StaticSymbol:
    """A global or file scope static, and what it costs.

    Attributes:
        name: Name the debug information gives it.
        bytes_used: Size of the whole object, arrays and padding included.
        source: File it was declared in, or ``None`` when none is named.
        is_constant: Whether it is read only. On a target that usually
            means it costs flash rather than RAM, which is the
            difference between a table that matters to a budget and one
            that does not.
    """

    name: str
    bytes_used: int
    source: PurePath | None = None
    is_constant: bool = False

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("A static symbol has a name")
        if self.bytes_used <= 0:
            raise ValueError(f"'{self.name}' would occupy {self.bytes_used} bytes")
