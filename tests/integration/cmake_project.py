"""Configuring, building and running the example through CMake.

Driving a build system from a test is mostly waiting on subprocesses and
deciding which tools are present. That part is here, so the tests can say
what they are checking.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = PROJECT_ROOT / "examples" / "blinky"
#: Where the C runtime is checked out. The examples default to the
#: neighbouring directory; a copy of one made outside the repository has
#: to be told the absolute path instead.
RUNTIME_ROOT = PROJECT_ROOT.parent / "looper-rt"
EXECUTABLE_NAME = "blinky.exe" if sys.platform == "win32" else "blinky"

CONFIGURE_TIMEOUT_SECONDS = 180.0
BUILD_TIMEOUT_SECONDS = 300.0
RUN_TIMEOUT_SECONDS = 60.0

# The simulation runs on a virtual clock for a fixed number of iterations, so
# a test does not depend on how fast the host is.
RUN_ARGUMENTS = ("--virtual", "--steps", "50", "--port", "0")


def tool(name: str) -> str:
    """Path of a build tool, skipping the test when it is absent."""
    found = shutil.which(name)
    if found is None:
        pytest.skip(f"{name} is not on PATH")
    return found


def compiler() -> str:
    """A compiler CMake can use, skipping when there is none."""
    found = shutil.which("gcc") or shutil.which("clang")
    if found is None:
        pytest.skip("no C compiler on PATH")
    return found


def generator() -> str:
    """A build generator that suits the compiler CMake was given.

    CMake defaults to the toolchain of the platform, which on Windows is the
    Microsoft one. A project building with gcc there needs to be told
    otherwise, and Ninja is what both platforms have in common.
    """
    if shutil.which("ninja") is not None:
        return "Ninja"
    if sys.platform == "win32":
        pytest.skip("no ninja on PATH, and the default generator does not suit gcc")
    return "Unix Makefiles"


def configure(
    project: Path, build_directory: Path, *options: str
) -> subprocess.CompletedProcess[str]:
    """Run CMake's configure step and return what it did.

    The result is returned rather than asserted on, because one test is
    about configuring failing in a particular way.
    """
    return subprocess.run(  # noqa: S603
        [
            tool("cmake"),
            "-S",
            str(project),
            "-B",
            str(build_directory),
            "-G",
            generator(),
            f"-DCMAKE_C_COMPILER={compiler()}",
            f"-DLOOPER_CLI={sys.executable} -m looper.presentation.cli.main",
            *options,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=CONFIGURE_TIMEOUT_SECONDS,
    )


def configured(build_directory: Path, *options: str) -> None:
    """Configure the example in place, failing with what CMake said."""
    completed = configure(EXAMPLE, build_directory, *options)
    assert completed.returncode == 0, completed.stdout + completed.stderr


def built(build_directory: Path) -> Path:
    """Build and return the executable it produced."""
    completed = subprocess.run(  # noqa: S603
        [tool("cmake"), "--build", str(build_directory)],
        capture_output=True,
        text=True,
        check=False,
        timeout=BUILD_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    executable = build_directory / EXECUTABLE_NAME
    assert executable.is_file(), f"nothing built at {executable}"
    return executable


def runs(executable: Path) -> str:
    """Start the simulation for a few iterations and return what it said."""
    completed = subprocess.run(  # noqa: S603
        [str(executable), *RUN_ARGUMENTS],
        capture_output=True,
        text=True,
        check=False,
        timeout=RUN_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return completed.stdout


def copied_project(tmp_path: Path, **replacements: str) -> Path:
    """A copy of the example outside the repository, with edits applied.

    Copying is what makes it answer like a project of its own: it has to
    name the runtime where the runtime really is rather than relative to
    a checkout it is no longer inside. A double underscore in a keyword
    stands for a space, which is the only way to pass a phrase as one.
    """
    project = tmp_path / "project"
    shutil.copytree(EXAMPLE, project, ignore=shutil.ignore_patterns("build"))
    definition = project / "CMakeLists.txt"
    content = definition.read_text(encoding="utf-8").replace(
        "${CMAKE_CURRENT_LIST_DIR}/../../../looper-rt", RUNTIME_ROOT.as_posix()
    )
    for old, new in replacements.items():
        content = content.replace(old.replace("__", " "), new)
    definition.write_text(content, encoding="utf-8")
    return project
