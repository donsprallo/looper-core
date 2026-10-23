"""Identity of a simulated general purpose IO pin."""

from __future__ import annotations

from dataclasses import dataclass, field

MAXIMUM_PIN_VALUE = 0xFFFF_FFFF


@dataclass(frozen=True)
class PinIdentifier:
    """A pin as addressed by the firmware, with an optional readable label.

    The adapter addresses pins by an opaque 32 bit value. That value is stable
    but meaningless to a human, so a label can be attached for display. The
    label is deliberately excluded from comparison and hashing: two identifiers
    with the same value address the same pin regardless of labelling.

    Attributes:
        value: Opaque pin number used by the firmware.
        label: Readable pin name shown by clients, if one is known.
    """

    value: int
    label: str | None = field(default=None, compare=False)

    def __post_init__(self) -> None:
        if not 0 <= self.value <= MAXIMUM_PIN_VALUE:
            raise ValueError(f"Pin value {self.value} is outside the 32 bit range")

    @property
    def display_name(self) -> str:
        """Label if one is known, otherwise the hexadecimal pin value."""
        return self.label if self.label else f"0x{self.value:08X}"

    def labelled(self, label: str) -> PinIdentifier:
        """Return the same pin carrying the given display label."""
        return PinIdentifier(value=self.value, label=label)
