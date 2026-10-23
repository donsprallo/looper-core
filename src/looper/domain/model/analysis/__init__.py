"""What an inspection of a project found, before anything is run."""

from __future__ import annotations

from looper.domain.model.analysis.call_site import (
    ArgumentStorage,
    CallArgument,
    CallSite,
)
from looper.domain.model.analysis.finding import (
    AnalysisReport,
    Finding,
    FindingKind,
    SourceLocation,
)
from looper.domain.model.analysis.firmware_usage import FirmwareUsage

__all__ = [
    "AnalysisReport",
    "ArgumentStorage",
    "CallArgument",
    "CallSite",
    "Finding",
    "FindingKind",
    "FirmwareUsage",
    "SourceLocation",
]
