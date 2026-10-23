"""Derivation of module names from adapter header file names."""

from __future__ import annotations

from pathlib import Path

DEFAULT_HEADER_PREFIX = "adapter_"
HEADER_SUFFIX = ".h"


def module_name_from_header(header_path: Path, prefix: str = DEFAULT_HEADER_PREFIX) -> str:
    """Derive a short module name from an adapter header path.

    ``Inc/adapter_gpio.h`` becomes ``gpio``. A header that does not carry the
    expected prefix keeps its full stem, because silently reinterpreting an
    unexpected name would hide a mis-configured header directory.

    Args:
        header_path: Path of the header file.
        prefix: Naming prefix shared by the adapter headers.

    Returns:
        The derived module name.

    Raises:
        ValueError: If the path does not name a C header file.
    """
    if header_path.suffix != HEADER_SUFFIX:
        raise ValueError(f"'{header_path}' is not a C header file")
    stem = header_path.stem
    if not stem.startswith(prefix):
        return stem
    return stem[len(prefix) :]
