"""Translation of an inspection into something a report can print."""

from __future__ import annotations

from looper.application.dto import AuditView, FindingView
from looper.domain.model.analysis import AnalysisReport, Finding


def build_audit_view(report: AnalysisReport) -> AuditView:
    """Describe everything an inspection found."""
    return AuditView(
        findings=tuple(_finding_view(finding) for finding in report.findings),
        coverage_note=report.coverage_note,
        is_clean=report.is_clean,
    )


def _finding_view(finding: Finding) -> FindingView:
    """Describe one finding."""
    return FindingView(
        kind=finding.kind.value,
        subject=finding.subject,
        detail=finding.detail,
        where=finding.location.text if finding.location is not None else "",
        is_a_defect=finding.kind.is_a_defect,
    )
