"""Data transfer objects exchanged with the use cases."""

from __future__ import annotations

from looper.application.dto.adapter_surface_report import (
    AdapterSurfaceReport,
    ContractGapSummary,
    ModuleSummary,
)
from looper.application.dto.analog_view import (
    ChannelView,
    SampleView,
    SignalView,
    TraceView,
)
from looper.application.dto.analyze_request import AnalyzeAdapterSurfaceRequest
from looper.application.dto.audit_view import AuditProjectRequest, AuditView, FindingView
from looper.application.dto.build_request import (
    BuildSimulationReport,
    BuildSimulationRequest,
    RunSimulationRequest,
)
from looper.application.dto.bus_view import (
    BusTraceView,
    BusView,
    ComponentView,
    ExchangeView,
)
from looper.application.dto.flame_view import FlameView, FrameView
from looper.application.dto.generate_request import (
    GeneratedFileSummary,
    GenerateSimulationReport,
    GenerateSimulationRequest,
)
from looper.application.dto.ladder_view import LadderView, PartyView, StepView
from looper.application.dto.memory_view import (
    AllocationSiteView,
    HeapUsageView,
    MemoryView,
    StackFrameView,
    StackUsageView,
    StaticMemoryView,
    StaticObjectView,
)
from looper.application.dto.profile_view import (
    ProfileEntryView,
    ProfileGroupView,
    ProfileView,
)
from looper.application.dto.simulation_view import PinView, SimulationView
from looper.application.dto.timeline_view import (
    CurveView,
    LaneView,
    MarkView,
    TimelineView,
    WindowView,
)
from looper.application.dto.timing_view import CallTimingView, TimingReportView
from looper.application.dto.variable_view import VariableView, WatchView

__all__ = [
    "FrameView",
    "FlameView",
    "StepView",
    "PartyView",
    "LadderView",
    "WindowView",
    "TimelineView",
    "MarkView",
    "LaneView",
    "CurveView",
    "AllocationSiteView",
    "HeapUsageView",
    "MemoryView",
    "StackFrameView",
    "StackUsageView",
    "StaticMemoryView",
    "StaticObjectView",
    "ProfileEntryView",
    "ProfileGroupView",
    "ProfileView",
    "AuditProjectRequest",
    "AuditView",
    "FindingView",
    "TimingReportView",
    "CallTimingView",
    "ComponentView",
    "ExchangeView",
    "BusTraceView",
    "BusView",
    "AdapterSurfaceReport",
    "AnalyzeAdapterSurfaceRequest",
    "BuildSimulationReport",
    "BuildSimulationRequest",
    "ChannelView",
    "ContractGapSummary",
    "GenerateSimulationReport",
    "GenerateSimulationRequest",
    "GeneratedFileSummary",
    "ModuleSummary",
    "PinView",
    "RunSimulationRequest",
    "SampleView",
    "SignalView",
    "TraceView",
    "SimulationView",
    "VariableView",
    "WatchView",
]
