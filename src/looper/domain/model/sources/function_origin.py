"""Where a measured function comes from.

A profile of a simulation mixes four kinds of code that happen to run in
one process, and the difference matters more than the names do. Time in
the firmware is what the firmware costs. Time in the device model is the
price of the simulation standing in for a board. Time in the generated
adapter is the boundary between the two. Time in the runtime is the
measuring apparatus.

The origin is decided by where a function was compiled from, which the
debug information says and nobody has to maintain. A function the debug
information does not describe at all was not compiled here: it came out
of a library, and that is the one origin recognised by absence.
"""

from __future__ import annotations

from enum import Enum, unique


@unique
class FunctionOrigin(Enum):
    """Which part of a simulation a function belongs to."""

    FIRMWARE = "firmware"
    DEVICE_MODEL = "device model"
    ADAPTER = "adapter"
    COMPONENT = "component"
    RUNTIME = "runtime"
    LIBRARY = "library"

    @property
    def is_the_firmware_itself(self) -> bool:
        """Whether this is the code under test rather than what holds it up."""
        return self is FunctionOrigin.FIRMWARE

    @property
    def is_measured_by_choice(self) -> bool:
        """Whether a project asks for this origin to be instrumented.

        Only the firmware and the model standing in for its board are
        instrumented. The adapter is already measured at its boundary,
        where it can also say whether anything answered; the runtime is
        the apparatus doing the measuring; and a library arrives already
        compiled, so nothing can be woven into it.
        """
        return self in (FunctionOrigin.FIRMWARE, FunctionOrigin.DEVICE_MODEL)
