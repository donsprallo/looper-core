"""Simulation runner that starts the executable as a child process."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

from looper.domain.ports import SimulationRunner

INTERRUPTED_EXIT_CODE = 0


class SubprocessSimulationRunner(SimulationRunner):
    """Runs a built simulation in the foreground.

    The simulation inherits the terminal, so its output appears as it is
    produced and Ctrl+C reaches it directly. An interrupt is reported as a
    clean stop rather than a failure, because stopping a simulation by hand is
    the normal way to end it.
    """

    def run(self, executable: Path, arguments: Sequence[str]) -> int:
        """Run the executable until it stops."""
        command = [str(executable), *arguments]
        try:
            return subprocess.run(command, check=False).returncode
        except KeyboardInterrupt:
            return INTERRUPTED_EXIT_CODE
