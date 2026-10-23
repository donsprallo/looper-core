"""What an inspection of a project found, before anything is run.

A simulation can be wrong in ways that a successful build and a quiet run
both hide. An exported table of function pointers that nobody filled links
and then dispatches to address zero. A buffer the adapter keeps a pointer
to, handed a local that goes out of scope, works until the timing changes.
A function the firmware calls that nothing implements returns zero and is
believed.

Each of those is knowable from what the project already writes down: the
adapter surface, the contract, and the firmware's own source. A finding is
one of them, with enough detail to act on and the place it was found.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from pathlib import Path


@unique
class FindingKind(Enum):
    """What sort of thing was found."""

    EXPORTED_DATA_WITHOUT_INITIALISER = "exported_data_without_initialiser"
    BUS_FUNCTION_WITHOUT_ROLE = "bus_function_without_role"
    BORROWED_POINTER_TO_LOCAL = "borrowed_pointer_to_local"
    NEVER_CALLED = "never_called"

    @property
    def is_a_defect(self) -> bool:
        """Whether this is something wrong rather than something to know.

        A function the firmware never calls is worth listing and is not a
        fault; the other three are faults waiting for the right timing.
        """
        return self is not FindingKind.NEVER_CALLED


@dataclass(frozen=True)
class SourceLocation:
    """Where in the project something was found.

    Attributes:
        path: File it was found in.
        line: Line within that file, counted from one.
    """

    path: Path
    line: int

    def __post_init__(self) -> None:
        if self.line < 1:
            raise ValueError("A source line is counted from one")

    @property
    def text(self) -> str:
        """The place as an editor understands it."""
        return f"{self.path.name}:{self.line}"


@dataclass(frozen=True)
class Finding:
    """One thing an inspection found.

    Attributes:
        kind: What sort of thing it is.
        subject: What it is about, named as the project names it.
        detail: What is wrong, and what follows from it.
        location: Where it was found, when there is a place to point at.
    """

    kind: FindingKind
    subject: str
    detail: str
    location: SourceLocation | None = None

    @property
    def line(self) -> str:
        """One line, as a report prints it."""
        where = f"  {self.location.text}" if self.location is not None else ""
        return f"{self.subject}{where}\n    {self.detail}"


@dataclass(frozen=True)
class AnalysisReport:
    """Everything one inspection found, and how much it could read.

    An inspection that could not read part of the firmware has to say so.
    A clean report over half the sources is not a clean report, and the
    difference has to be visible rather than inferred from a silence.

    Attributes:
        findings: What was found, in the order the checks ran.
        units_read: Translation units the front end could read.
        units_unreadable: Translation units it could not.
    """

    findings: tuple[Finding, ...] = field(default_factory=tuple)
    units_read: int = 0
    units_unreadable: int = 0

    @property
    def defects(self) -> tuple[Finding, ...]:
        """The findings that are something wrong."""
        return tuple(finding for finding in self.findings if finding.kind.is_a_defect)

    @property
    def is_clean(self) -> bool:
        """Whether nothing wrong was found, and everything could be read."""
        return not self.defects and self.units_unreadable == 0

    @property
    def coverage_note(self) -> str:
        """How much of the firmware the inspection managed to read."""
        total = self.units_read + self.units_unreadable
        if total == 0:
            return "no firmware source was read"
        if self.units_unreadable == 0:
            return f"read all {total} translation units"
        return f"read {self.units_read} of {total} translation units"
