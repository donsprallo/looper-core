"""Failures raised while reading adapter headers."""

from __future__ import annotations


class HeaderParseError(RuntimeError):
    """A header could not be translated into declarations.

    Attributes:
        header_path: Header the failure was raised for.
        messages: Compiler diagnostics that caused the failure.
    """

    def __init__(self, header_path: str, messages: tuple[str, ...]) -> None:
        self.header_path = header_path
        self.messages = messages
        super().__init__(self._describe())

    def _describe(self) -> str:
        """Build a message that names the header and every diagnostic."""
        details = "\n".join(f"  {message}" for message in self.messages)
        return f"Failed to parse '{self.header_path}':\n{details}"
