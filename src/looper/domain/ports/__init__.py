"""Abstract outbound interfaces for talking to a running simulation.

These are service ports rather than repositories: they address one live
firmware process, one build, or one executable, instead of a collection
of stored aggregates. The progress listener is the odd one out: it
addresses nothing at all, and is here because both the use cases and
the compiler driver report through it.
"""

from __future__ import annotations

from looper.domain.ports.analysis import FirmwareUsageReader
from looper.domain.ports.build import SimulationBuilder, SimulationRunner
from looper.domain.ports.codegen import AdapterSimulationGenerator
from looper.domain.ports.debug_information import DebugInformationReader
from looper.domain.ports.errors import SimulationRejectedError
from looper.domain.ports.progress import ProgressListener, SilentProgress
from looper.domain.ports.simulation_session import SimulationSession

__all__ = [
    "AdapterSimulationGenerator",
    "DebugInformationReader",
    "FirmwareUsageReader",
    "ProgressListener",
    "SimulationRejectedError",
    "SimulationBuilder",
    "SimulationRunner",
    "SimulationSession",
    "SilentProgress",
]
