"""Location of the C runtime and components a simulation is built from.

The C sources are a distribution of their own, `looper-rt`, so that a
firmware project that builds with CMake can take them without taking the
Python tooling. They are found here through the package rather than
through a path, which is what makes a checkout and an installed wheel
resolve to the same place.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import looper_rt

RUNTIME_DIRECTORY = "runtime"
COMPONENTS_DIRECTORY = "components"
SOURCE_DIRECTORY = "src"
INCLUDE_DIRECTORY = "include"
SOURCE_PATTERN = "*.c"
HEADER_PATTERN = "*.h"
COMPONENT_PREFIX = "looper_"


def runtime_root() -> Path:
    """Return the directory holding the C runtime.

    The runtime lives inside `looper-rt` rather than beside it, so that an
    installed wheel carries it and a checkout resolves to the same path.

    Raises:
        FileNotFoundError: If the installation is missing the runtime.
    """
    root = Path(looper_rt.__file__).parent / RUNTIME_DIRECTORY
    if not root.is_dir():
        raise FileNotFoundError(f"The looper runtime is missing from '{root}'")
    return root


def components_root() -> Path:
    """Return the directory holding the components that ship with looper.

    Raises:
        FileNotFoundError: If the installation is missing them.
    """
    root = Path(looper_rt.__file__).parent / COMPONENTS_DIRECTORY
    if not root.is_dir():
        raise FileNotFoundError(f"The looper components are missing from '{root}'")
    return root


def runtime_sources() -> tuple[Path, ...]:
    """Return every translation unit of the runtime, in a stable order."""
    return tuple(sorted((runtime_root() / SOURCE_DIRECTORY).glob(SOURCE_PATTERN)))


def available_components() -> tuple[str, ...]:
    """Return the name of every component that ships with looper.

    A component is what has a public header. Its implementation may be
    several translation units, and the private headers between them stay in
    the source directory, so the public ones are exactly the list.
    """
    headers = sorted((components_root() / INCLUDE_DIRECTORY).glob(HEADER_PATTERN))
    return tuple(header.stem.removeprefix(COMPONENT_PREFIX) for header in headers)


def component_sources(names: Iterable[str]) -> tuple[Path, ...]:
    """Return the translation unit of each named component.

    A project says which ones its board carries. Compiling them all would
    put a device in every simulation that nobody asked for, and would make
    the two build paths disagree: a direct build compiles what it is given,
    while a linker keeps only what a library is asked for.

    One component may be several translation units, so each name takes
    everything whose file name begins with it.

    Raises:
        FileNotFoundError: If a name is not one of the components.
    """
    root = components_root() / SOURCE_DIRECTORY
    offered = available_components()
    resolved: list[Path] = []
    for name in names:
        if name not in offered:
            raise FileNotFoundError(
                f"'{name}' is not a looper component; there are {', '.join(offered)}"
            )
        resolved.extend(sorted(root.glob(f"{COMPONENT_PREFIX}{name}*{SOURCE_PATTERN[1:]}")))
    return tuple(resolved)


def runtime_include_directory() -> Path:
    """Return the include directory of the runtime."""
    return runtime_root() / INCLUDE_DIRECTORY


def runtime_include_directories() -> tuple[Path, ...]:
    """Return every include directory a simulation compiles against."""
    return (runtime_root() / INCLUDE_DIRECTORY, components_root() / INCLUDE_DIRECTORY)
