"""Which part of the running program a variable belongs to."""

from __future__ import annotations

from enum import Enum, unique


@unique
class VariableOrigin(Enum):
    """Whether a variable is the firmware's or the simulation's.

    Three programs end up in one executable: the firmware, the machinery
    that lets it run on a host and be looked at, and whatever the linker
    pulled out of the C runtime to make a process at all. All three have
    variables and the debug information describes all three, but only one
    of them is what anyone came to see. A client that shows the clock's
    ring buffer and the startup lock beside a measurement channel is
    burying the answer in the apparatus.

    The distinction is recorded rather than acted on here: whether the
    apparatus is worth showing is a question for whoever is looking.
    """

    FIRMWARE = "firmware"
    SIMULATION = "simulation"
    TOOLCHAIN = "toolchain"
