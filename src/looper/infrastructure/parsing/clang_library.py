"""Loading of the libclang shared library."""

from __future__ import annotations

from pathlib import Path

from clang import cindex

_library_configured = False


def create_index() -> cindex.Index:
    """Create a libclang index, loading the bundled library if required.

    ``clang.cindex`` looks for the shared library on the system search path
    first. The ``libclang`` wheel ships its own copy next to the Python module,
    which is used as a fallback so that the tool works without a system wide
    LLVM installation.

    Raises:
        RuntimeError: If no usable libclang library can be loaded.
    """
    global _library_configured
    if not _library_configured:
        _configure_library()
        _library_configured = True
    return cindex.Index.create()


def _configure_library() -> None:
    """Point libclang at the bundled shared library when it is available."""
    bundled = _bundled_library_path()
    if bundled is None:
        return
    cindex.Config.set_library_file(str(bundled))


def _bundled_library_path() -> Path | None:
    """Locate the shared library shipped inside the ``clang`` package."""
    package_directory = Path(cindex.__file__).parent
    for name in ("libclang.dll", "libclang.so", "libclang.dylib"):
        candidates = sorted(package_directory.rglob(name))
        if candidates:
            return candidates[0]
    return None
