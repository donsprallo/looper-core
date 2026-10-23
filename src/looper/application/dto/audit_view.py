"""Data transfer objects describing what an inspection found."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from looper.application.dto.memory_view import StaticMemoryView


class AuditProjectRequest(BaseModel):
    """Which project to inspect.

    How its sources are read is not part of this request. Include
    directories and definitions belong to the reader, so that the use
    case stays independent of the front end behind it.

    Attributes:
        definition_path: Build definition of the project to inspect.
    """

    model_config = ConfigDict(frozen=True)

    definition_path: Path


class FindingView(BaseModel):
    """One thing an inspection found, ready to be printed.

    Attributes:
        kind: What sort of thing it is.
        subject: What it is about, named as the project names it.
        detail: What is wrong, and what follows from it.
        where: Where it was found, or empty when there is no place.
        is_a_defect: Whether it is something wrong rather than to know.
    """

    model_config = ConfigDict(frozen=True)

    kind: str
    subject: str
    detail: str
    where: str = ""
    is_a_defect: bool = True

    @property
    def line(self) -> str:
        """The finding on one line, with its place when it has one."""
        return f"{self.subject}{f'  {self.where}' if self.where else ''}"


class AuditView(BaseModel):
    """Everything one inspection found, and how much it could read.

    Attributes:
        findings: What was found, worst first.
        coverage_note: How much of the project the inspection read.
        is_clean: Whether nothing wrong was found and all was read.
        static_memory: What the built simulation holds before it runs,
            or ``None`` when there was nothing built to read it from.
            The audit otherwise needs no build, so this is the one part
            of it that appears only once there is one.
        memory_note: Why there is no static memory, when there is none.
    """

    model_config = ConfigDict(frozen=True)

    findings: tuple[FindingView, ...] = ()
    coverage_note: str = ""
    is_clean: bool = True
    static_memory: StaticMemoryView | None = None
    memory_note: str = ""

    @property
    def defects(self) -> tuple[FindingView, ...]:
        """The findings that are something wrong."""
        return tuple(finding for finding in self.findings if finding.is_a_defect)

    @property
    def notes(self) -> tuple[FindingView, ...]:
        """The findings that are only worth knowing."""
        return tuple(finding for finding in self.findings if not finding.is_a_defect)

    def of_kind(self, kind: str) -> tuple[FindingView, ...]:
        """Every finding of one kind, in the order they were found."""
        return tuple(finding for finding in self.findings if finding.kind == kind)

    @property
    def is_over_budget(self) -> bool:
        """Whether a memory budget was set and the build does not fit."""
        return (self.static_memory is not None) and not self.static_memory.is_within_budget

    @property
    def has_nothing_to_act_on(self) -> bool:
        """Whether everything the audit looked at was in order."""
        return self.is_clean and not self.is_over_budget
