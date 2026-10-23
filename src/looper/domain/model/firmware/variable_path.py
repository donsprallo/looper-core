"""Where a scalar sits inside a firmware variable."""

from __future__ import annotations

from dataclasses import dataclass

from looper.domain.model.c_api.validation import ensure_non_empty

MEMBER_SEPARATOR = "."
SUBSCRIPT_OPEN = "["
SUBSCRIPT_CLOSE = "]"
PATH_SEPARATORS = (MEMBER_SEPARATOR, SUBSCRIPT_OPEN)


@dataclass(frozen=True)
class VariablePath:
    """The name under which a client addresses one scalar.

    The root is a variable with static storage. The rest of the path walks
    into structures and arrays until a scalar is reached, written the way the
    firmware source would write it::

        g_app_config.active.measurement.channel[0].calibration.gain

    The path is an identity and a label. It is not how the simulation finds
    the value: that is an address, resolved once from the debug information.
    A path therefore stays meaningful only for the build it was read from.

    Attributes:
        text: The path as written.
    """

    text: str

    def __post_init__(self) -> None:
        ensure_non_empty(self.text, "A variable path")
        if self.text != self.text.strip():
            raise ValueError(f"Variable path '{self.text}' has surrounding whitespace")

    @property
    def root(self) -> str:
        """Name of the variable with static storage the path starts at."""
        for index, character in enumerate(self.text):
            if character in PATH_SEPARATORS:
                return self.text[:index]
        return self.text

    @property
    def leaf(self) -> str:
        """Last member of the path, which is the scalar itself."""
        _, separator, member = self.text.rpartition(MEMBER_SEPARATOR)
        return member if separator else self.text

    @property
    def segments(self) -> tuple[str, ...]:
        """The path broken into the steps a client walks it by.

        A subscript is a step of its own, so that an array can be opened and
        its elements listed the way a structure's members are::

            g_config.channel[1].gain
            -> ("g_config", "channel", "[1]", "gain")
        """
        found: list[str] = []
        for member in self.text.split(MEMBER_SEPARATOR):
            found.extend(_split_subscripts(member))
        return tuple(found)

    @property
    def is_root(self) -> bool:
        """Whether the path names a whole variable rather than a part of one."""
        return self.text == self.root

    def __str__(self) -> str:
        return self.text


def _split_subscripts(member: str) -> list[str]:
    """Separate a member from the subscripts applied to it."""
    opened = member.find(SUBSCRIPT_OPEN)
    if opened < 0:
        return [member] if member else []
    parts = [member[:opened]] if opened > 0 else []
    rest = member[opened:]
    while rest.startswith(SUBSCRIPT_OPEN):
        closed = rest.find(SUBSCRIPT_CLOSE)
        if closed < 0:
            break
        parts.append(rest[: closed + 1])
        rest = rest[closed + 1 :]
    if rest:
        parts.append(rest)
    return parts
