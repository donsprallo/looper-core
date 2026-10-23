"""One adapter call, as the journal recorded it.

The timing report says a function was called four thousand times and
what one call cost on average. The journal says *when* each of them
happened, which is the only one of the two that can be put beside a
bus exchange and a measured value on the same ruler.

What it does not say is how long the call lasted. The journal records
the moment a call was made and nothing else, so a drawing gets a tick
rather than a bar -- and a tick that pretends to be a bar would be an
invented duration.
"""

from __future__ import annotations

from dataclasses import dataclass

MICROSECONDS_PER_SECOND = 1_000_000.0

#: What separates an adapter function's name from its peripheral, which
#: is how calls are gathered into one lane per peripheral.
NAME_SEPARATOR = "_"

#: Every adapter function the generator writes begins with this.
NAME_PREFIX = "adapter_"


@dataclass(frozen=True)
class AdapterCall:
    """One call the firmware made into its adapter.

    Attributes:
        function: Name of the adapter function.
        microseconds: Simulated time the call was made at.
        sequence: Position in the recording, used to read incrementally.
    """

    function: str
    microseconds: int = 0
    sequence: int = 0

    def __post_init__(self) -> None:
        if not self.function:
            raise ValueError("A recorded call names the function it called")
        if self.microseconds < 0:
            raise ValueError(f"'{self.function}' cannot have been called at a negative time")

    @property
    def seconds(self) -> float:
        """Recording time in seconds, for lining up with everything else."""
        return self.microseconds / MICROSECONDS_PER_SECOND

    @property
    def peripheral(self) -> str:
        """Which part of the board the call belongs to.

        Taken from the name, because the journal carries nothing else:
        `adapter_spi_transfer` belongs to `spi`. A convention rather
        than a fact, but it is the generator's own convention, and a
        row per peripheral is what makes a hundred calls readable.
        """
        rest = self.function.removeprefix(NAME_PREFIX)
        head, separator, _ = rest.partition(NAME_SEPARATOR)
        return head if separator else rest
