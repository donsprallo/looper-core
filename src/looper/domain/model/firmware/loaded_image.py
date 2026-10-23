"""Where the running process put the image the debug information describes."""

from __future__ import annotations

from dataclasses import dataclass

from looper.domain.model.firmware.firmware_variable import FirmwareVariable


@dataclass(frozen=True)
class LoadedImage:
    """The distance between link time addresses and the running process.

    Debug information names the addresses the linker chose. An operating
    system that relocates an image when it loads it -- which Windows and Linux
    both do by default -- puts it somewhere else, and every address shifts by
    the same distance. Reading a variable in the running process means
    applying that shift first.

    The simulation reports both bases rather than the difference alone,
    because the pair says where the image actually is and the difference only
    says how far it moved.

    A position independent executable is linked against a base of zero, so
    that is a base like any other rather than a missing one.

    Attributes:
        link_time_base: Base address the debug information is written against.
        runtime_base: Base address the process was actually loaded at.
    """

    link_time_base: int
    runtime_base: int

    def __post_init__(self) -> None:
        if self.link_time_base < 0:
            raise ValueError("An image has no usable link time base")
        if self.runtime_base <= 0:
            raise ValueError("An image has no usable runtime base")

    @property
    def slide(self) -> int:
        """Distance every link time address has to be moved by."""
        return self.runtime_base - self.link_time_base

    @property
    def is_relocated(self) -> bool:
        """Whether the process was loaded somewhere other than its link address."""
        return self.slide != 0

    def runtime_address_of(self, variable: FirmwareVariable) -> int:
        """Translate a variable's link time address into the running process.

        Args:
            variable: Variable read from the debug information.

        Returns:
            The address to read in the running process.

        Raises:
            ValueError: If the translated address is not a usable address,
                which means the image and the debug information disagree.
        """
        address = variable.link_time_address + self.slide
        if address <= 0:
            raise ValueError(
                f"Variable '{variable.path}' translates to {address:#x}, "
                "so the debug information does not belong to this process"
            )
        return address
