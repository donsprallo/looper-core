"""What a build holds in memory before it does anything at all.

Every global and every file scope static costs its bytes from the
moment the image is loaded, whether or not anything ever touches it.
On a host that hardly matters. On a microcontroller it is the first
number anybody asks for, and it is the one kind of memory a simulation
can describe without being run: the debug information in the executable
already says how big each object is and which file it came from.

What transfers to the target and what does not is worth being exact
about. The structure does: a firmware holding one 28 KiB table holds it
there too. The bytes do not, quite -- a pointer is eight bytes here and
four there, and two compilers pad a structure differently. So this is a
way of finding what is large and where it lives, not a budget to sign
off against.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePath

from looper.domain.model.sources import FunctionOrigin

BYTES_PER_KIBIBYTE = 1024


@dataclass(frozen=True)
class StaticObject:
    """One global or file scope static, and what it costs.

    Attributes:
        name: Name the debug information gives it.
        origin: Which part of the simulation it belongs to.
        source: File it was declared in, when one is known.
        bytes_used: Size of the whole object, arrays and padding included.
        is_constant: Whether it is read only, which on a target usually
            means it costs flash rather than RAM.
    """

    name: str
    origin: FunctionOrigin
    source: PurePath | None = None
    bytes_used: int = 0
    is_constant: bool = False

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("A static object has a name")
        if self.bytes_used < 0:
            raise ValueError(f"'{self.name}' cannot occupy {self.bytes_used} bytes")

    @property
    def directory(self) -> str:
        """Where the object's source lives, as a report groups by it."""
        return str(self.source.parent) if self.source is not None else ""

    @property
    def file_name(self) -> str:
        """The source file alone, without the path to it."""
        return self.source.name if self.source is not None else ""


@dataclass(frozen=True)
class StaticMemoryReport:
    """Everything a build holds statically, and where.

    Attributes:
        objects: Every object found, in no particular order.
        budget_bytes: What the project allows itself, or zero for no
            limit. A budget is the project's own number and is checked
            against the simulation's bytes, which is a guide rather
            than a measurement of the target.
    """

    objects: tuple[StaticObject, ...] = field(default_factory=tuple)
    budget_bytes: int = 0

    def __post_init__(self) -> None:
        if self.budget_bytes < 0:
            raise ValueError("A memory budget is not negative")

    @property
    def total_bytes(self) -> int:
        """What every object adds up to."""
        return sum(one.bytes_used for one in self.objects)

    @property
    def writable_bytes(self) -> int:
        """What the objects that are not read only add up to.

        The number closest to a target's RAM: a constant table is in
        flash there, and only what can be written costs memory.
        """
        return sum(one.bytes_used for one in self.objects if not one.is_constant)

    @property
    def is_within_budget(self) -> bool:
        """Whether the writable bytes fit what the project allows."""
        return (self.budget_bytes == 0) or (self.writable_bytes <= self.budget_bytes)

    @property
    def firmware_bytes(self) -> int:
        """What the firmware's own objects cost, machinery excluded."""
        return sum(
            one.bytes_used
            for one in self.objects
            if one.origin.is_the_firmware_itself and not one.is_constant
        )

    def biggest(self, count: int) -> tuple[StaticObject, ...]:
        """The largest objects, which is where a budget goes."""
        ordered = sorted(self.objects, key=lambda one: (-one.bytes_used, one.name))
        return tuple(ordered[:count])

    def by_directory(self) -> tuple[tuple[str, int], ...]:
        """What each source directory holds, heaviest first."""
        gathered: dict[str, int] = {}
        for one in self.objects:
            gathered[one.directory] = gathered.get(one.directory, 0) + one.bytes_used
        return tuple(sorted(gathered.items(), key=lambda pair: (-pair[1], pair[0])))


def kibibytes(bytes_used: int) -> str:
    """A size as a report prints it."""
    if bytes_used < BYTES_PER_KIBIBYTE:
        return f"{bytes_used} B"
    return f"{bytes_used / BYTES_PER_KIBIBYTE:.1f} KiB"
