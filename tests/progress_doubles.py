"""A listener that writes down what a use case said it was doing.

Which steps are announced, and in which order, is part of what a use
case promises: a command line publishes the plan before the work
starts and draws a bar against it. A listener that records is how a
test reads that promise back without a terminal.
"""

from __future__ import annotations

from looper.domain.ports import ProgressListener


class RecordingProgress(ProgressListener):
    """Keeps every announcement, in order.

    Attributes:
        announced: What each step said it was about to do.
        summaries: What each step that finished came to. A step that
            raised leaves nothing here, which is how an open step is
            told from a closed one.
        fractions: How far through itself a step said it was, each
            time it said so.
    """

    def __init__(self) -> None:
        self.announced: list[str] = []
        self.summaries: list[str] = []
        self.fractions: list[tuple[int, int, str]] = []

    def begin(self, activity: str) -> None:
        """Write down the step that is starting."""
        self.announced.append(activity)

    def end(self, summary: str = "") -> None:
        """Write down what it came to."""
        self.summaries.append(summary)

    def advance(self, done: int, total: int, detail: str = "") -> None:
        """Write down how far through itself the step said it was."""
        self.fractions.append((done, total, detail))

    @property
    def open_steps(self) -> int:
        """How many steps were begun and never finished."""
        return len(self.announced) - len(self.summaries)
