"""Use cases that read without changing anything."""

from __future__ import annotations

from looper.application.queries.analyze_adapter_surface import AnalyzeAdapterSurface
from looper.application.queries.audit_project import AuditProject
from looper.application.queries.inspect_variables import ListFirmwareVariables, ObserveWatches
from looper.application.queries.observe_analog import ObserveChannels, ReadTrace
from looper.application.queries.observe_buses import (
    ObserveBuses,
    ObserveComponents,
    ReadBusTrace,
)
from looper.application.queries.observe_flame import ObserveFlame
from looper.application.queries.observe_ladder import ObserveLadder
from looper.application.queries.observe_memory import ObserveMemory
from looper.application.queries.observe_profile import ObserveProfile
from looper.application.queries.observe_simulation import ObserveSimulation
from looper.application.queries.observe_timeline import ObserveTimeline
from looper.application.queries.observe_timings import ObserveCallTimings

__all__ = [
    "ObserveMemory",
    "ObserveFlame",
    "ObserveLadder",
    "ObserveProfile",
    "ObserveTimeline",
    "AuditProject",
    "ObserveCallTimings",
    "ObserveComponents",
    "ReadBusTrace",
    "ObserveBuses",
    "AnalyzeAdapterSurface",
    "ListFirmwareVariables",
    "ObserveChannels",
    "ObserveSimulation",
    "ObserveWatches",
    "ReadTrace",
]
