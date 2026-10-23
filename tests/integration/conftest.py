"""The example simulation, built once and started per test.

Both integration modules drive the same example firmware, so building it and
starting it live here rather than in either of them. A machine without a
compiler skips at the fixture, which is what makes the tests that depend on a
running simulation skip without each of them saying so.
"""

from __future__ import annotations

import shutil
import socket
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from layout_fixture import build_fixture, compiler_on_path

from looper.domain.model.firmware import FirmwareVariable, LoadedImage
from looper.infrastructure.debug import DwarfDebugReader
from looper.infrastructure.ipc import ProtobufSimulationSession

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFINITION = PROJECT_ROOT / "examples" / "blinky" / "looper.toml"
EXECUTABLE = (
    PROJECT_ROOT
    / "examples"
    / "blinky"
    / "build"
    / ("blinky.exe" if sys.platform == "win32" else "blinky")
)

STARTUP_TIMEOUT_SECONDS = 10.0
POLL_INTERVAL_SECONDS = 0.02


def free_port() -> int:
    """Ask the operating system for a port nobody is listening on."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


@pytest.fixture(scope="session")
def simulation_executable() -> Path:
    """Generate and build the example simulation once per test session."""
    if shutil.which("gcc") is None and shutil.which("clang") is None:
        pytest.skip("no C compiler on PATH")
    built = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "looper.presentation.cli.main", "build", str(DEFINITION)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert built.returncode == 0, built.stderr or built.stdout
    assert EXECUTABLE.is_file(), f"nothing built at {EXECUTABLE}"
    return EXECUTABLE


def start_simulation(executable: Path, *arguments: str) -> tuple[subprocess.Popen[bytes], int]:
    """Start the simulation on a free port."""
    port = free_port()
    process = subprocess.Popen(  # noqa: S603
        [str(executable), "--port", str(port), *arguments],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return process, port


def connect(port: int) -> ProtobufSimulationSession:
    """Connect once the simulation is listening."""
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            return ProtobufSimulationSession(port=port)
        except ConnectionError:
            time.sleep(POLL_INTERVAL_SECONDS)
    raise AssertionError("the simulation never started listening")


def _session(executable: Path, *arguments: str) -> Iterator[ProtobufSimulationSession]:
    """Start a simulation, hand out a session, and stop it afterwards.

    Connecting is inside the block that stops the process, because it is
    a step that can fail: a simulation this client cannot talk to is
    still a simulation that is running, and leaving it behind holds its
    executable open against the next build.
    """
    process, port = start_simulation(executable, *arguments)
    try:
        session = connect(port)
        try:
            yield session
        finally:
            session.close()
    finally:
        process.terminate()
        process.wait(timeout=STARTUP_TIMEOUT_SECONDS)


@pytest.fixture
def real_time_session(simulation_executable: Path) -> Iterator[ProtobufSimulationSession]:
    """A session against a simulation running on the host clock."""
    yield from _session(simulation_executable)


@pytest.fixture
def virtual_time_session(simulation_executable: Path) -> Iterator[ProtobufSimulationSession]:
    """A session against a simulation running on a virtual clock."""
    yield from _session(simulation_executable, "--virtual")


@pytest.fixture(scope="session")
def fixture_build(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, tuple[int, int, int]]:
    """Compile the layout fixture once per test session."""
    compiler = compiler_on_path()
    if compiler is None:
        pytest.skip("no C compiler on PATH")
    return build_fixture(tmp_path_factory.mktemp("dwarf"), compiler)


@pytest.fixture(scope="session")
def fixture_variables(
    fixture_build: tuple[Path, tuple[int, int, int]],
) -> dict[str, FirmwareVariable]:
    """Every variable the reader finds in the compiled layout fixture."""
    executable, _ = fixture_build
    return {
        variable.path.text: variable for variable in DwarfDebugReader().read_variables(executable)
    }


@pytest.fixture
def reader() -> DwarfDebugReader:
    """A reader over the debug information of the built simulation."""
    return DwarfDebugReader()


@pytest.fixture
def executable(virtual_time_session: ProtobufSimulationSession) -> Path:
    """The executable the running simulation reports as its own."""
    reported = virtual_time_session.executable
    assert reported is not None, "the simulation did not report its own path"
    return reported


@pytest.fixture
def image(
    virtual_time_session: ProtobufSimulationSession, reader: DwarfDebugReader, executable: Path
) -> LoadedImage:
    """Where the running process put the image the debug information describes."""
    return LoadedImage(
        link_time_base=reader.read_link_time_base(executable),
        runtime_base=virtual_time_session.read_runtime_base(),
    )


@pytest.fixture
def variables(reader: DwarfDebugReader, executable: Path) -> dict[str, FirmwareVariable]:
    """Every global the running simulation describes, by path."""
    return {variable.path.text: variable for variable in reader.read_variables(executable)}


@pytest.fixture
def watch(
    virtual_time_session: ProtobufSimulationSession,
    image: LoadedImage,
    variables: dict[str, FirmwareVariable],
) -> Callable[[str], int]:
    """Start watching a variable by path and hand back its trace channel."""

    def start(path: str) -> int:
        variable = variables[path]
        started = virtual_time_session.watch_variable(variable, image.runtime_address_of(variable))
        return started.channel

    return start


@pytest.fixture
def watched_value(virtual_time_session: ProtobufSimulationSession) -> Callable[[int], float]:
    """Read back the value the simulation last sampled on a channel."""

    def value_of(channel: int) -> float:
        watches = {entry.channel: entry for entry in virtual_time_session.read_variable_watches()}
        return watches[channel].value

    return value_of
