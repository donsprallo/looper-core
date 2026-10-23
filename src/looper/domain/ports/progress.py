"""Where a long running job says what it is doing.

A build reads a definition, parses headers, renders sources and then
hands a hundred translation units to a compiler. From the outside that
is one long silence, and a silence is indistinguishable from a hang.
So the work narrates itself.

An outbound port like the others here: a use case announces its steps
and the compiler driver announces its units, and neither of them knows
whether anybody is drawing a line, writing a log, or listening at all.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class ProgressListener(ABC):
    """A sink for what a job is doing."""

    @abstractmethod
    def begin(self, activity: str) -> None:
        """Announce the step that is starting.

        Args:
            activity: What is being done, as a present participle, so
                that a reader sees the same grammar in every line.
        """

    @abstractmethod
    def end(self, summary: str = "") -> None:
        """Report that the step last begun has finished.

        A step that raises never ends. That is deliberate: whoever is
        drawing the progress sees an open step and can close it as the
        failure it was, rather than being told it succeeded.

        Args:
            summary: What the step produced, in a few words. Empty
                when it has nothing to show for itself.
        """

    @abstractmethod
    def advance(self, done: int, total: int, detail: str = "") -> None:
        """Report how far through itself the running step has got.

        Most steps are one call and never say this. What it is for is
        the step that is really a hundred of them -- the compiler --
        where knowing it is at the thirty-seventh is the difference
        between waiting and wondering. A listener that does not draw
        it says nothing and loses nothing.

        Args:
            done: How many parts of the step are finished.
            total: How many there are.
            detail: What the step is on, in a word or two.
        """


class SilentProgress(ProgressListener):
    """A listener for when nobody is watching.

    The default of every job, so that a caller with no interest in
    progress -- a test, the inspector, another use case -- keeps
    calling exactly as it did before there was any.
    """

    def begin(self, activity: str) -> None:
        """Say nothing."""

    def end(self, summary: str = "") -> None:
        """Say nothing."""

    def advance(self, done: int, total: int, detail: str = "") -> None:
        """Say nothing."""
