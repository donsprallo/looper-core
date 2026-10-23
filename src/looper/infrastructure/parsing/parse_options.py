"""Compiler arguments used when reading adapter headers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

STUB_INCLUDE_DIRECTORY = Path(__file__).parent / "stub_includes"
"""Freestanding stand-ins for the standard headers a firmware target provides."""

DEFAULT_LANGUAGE_STANDARD = "c11"


@dataclass(frozen=True)
class ParseOptions:
    """How libclang should be invoked for one adapter header directory.

    Firmware headers are written for a cross compiler, so the host's system
    headers are the wrong answer for ``<stdint.h>``. A minimal set of
    freestanding stand-ins is appended last instead, which keeps parsing
    portable. Supplying the real toolchain include directory takes precedence,
    because it is listed first.

    Attributes:
        include_directories: Directories searched for included headers.
        definitions: Preprocessor definitions in ``NAME`` or ``NAME=value`` form.
        language_standard: C standard passed to the compiler front end.
        use_stub_headers: Whether the bundled stand-in headers are appended.
    """

    include_directories: tuple[Path, ...] = field(default_factory=tuple)
    definitions: tuple[str, ...] = field(default_factory=tuple)
    language_standard: str = DEFAULT_LANGUAGE_STANDARD
    use_stub_headers: bool = True

    def clang_arguments(self) -> list[str]:
        """Build the command line passed to the libclang front end."""
        arguments = ["-x", "c", f"-std={self.language_standard}"]
        arguments.extend(f"-D{definition}" for definition in self.definitions)
        arguments.extend(f"-I{directory}" for directory in self.search_path)
        return arguments

    @property
    def search_path(self) -> tuple[Path, ...]:
        """Include directories in search order, stand-ins last."""
        if not self.use_stub_headers:
            return self.include_directories
        return (*self.include_directories, STUB_INCLUDE_DIRECTORY)
