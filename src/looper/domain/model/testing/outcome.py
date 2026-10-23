"""What came of checking one expectation, and of checking them all.

A check that only says "failed" makes someone run it again with prints in
it. Every outcome here carries what was expected and what was actually
seen, so the report is the whole investigation rather than the start of
one.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Outcome:
    """What came of checking one expectation.

    Attributes:
        subject: What was being checked, as a reader would name it.
        expected: What it was supposed to do.
        observed: What it did.
        met: Whether the two agree.
    """

    subject: str
    expected: str
    observed: str
    met: bool

    @property
    def line(self) -> str:
        """One line, as a report prints it."""
        mark = "ok  " if self.met else "FAIL"
        return f"{mark}  {self.subject}: expected {self.expected}, saw {self.observed}"


@dataclass(frozen=True)
class ExpectationReport:
    """What came of checking every expectation of one run.

    Attributes:
        outcomes: One per expectation, in the order they were declared.
    """

    outcomes: tuple[Outcome, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        """Whether every expectation was met."""
        return all(outcome.met for outcome in self.outcomes)

    @property
    def failures(self) -> tuple[Outcome, ...]:
        """The expectations that were not met."""
        return tuple(outcome for outcome in self.outcomes if not outcome.met)

    @property
    def summary(self) -> str:
        """The whole report, failures first, as a test failure prints it."""
        if not self.outcomes:
            return "nothing was expected"
        heading = f"{len(self.outcomes) - len(self.failures)} of {len(self.outcomes)} met"
        lines = [outcome.line for outcome in self.failures]
        lines.extend(outcome.line for outcome in self.outcomes if outcome.met)
        return "\n".join([heading, *lines])

    def __bool__(self) -> bool:
        """A report is true when everything was met, so `assert report` reads."""
        return self.passed
