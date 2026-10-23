"""Data transfer objects describing where a simulation spent its time."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ProfileEntryView(BaseModel):
    """One measured function, ready to be drawn.

    Attributes:
        name: Name the debug information gives it.
        origin: Which part of the simulation it belongs to.
        directory: Where its source lives.
        file_name: Its source file, without the path.
        calls: How often it was entered.
        self_nanoseconds: Host time spent in the function itself.
        total_nanoseconds: The same with its callees included.
        self_text: Self time as it is shown.
        total_text: Total time as it is shown.
        mean_text: Average call as it is shown.
        longest_text: Slowest single call as it is shown.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    origin: str
    directory: str = ""
    file_name: str = ""
    calls: int = 0
    self_nanoseconds: int = 0
    total_nanoseconds: int = 0
    self_text: str = ""
    total_text: str = ""
    mean_text: str = ""
    longest_text: str = ""


class ProfileGroupView(BaseModel):
    """A set of measured functions and what they cost together.

    Only self time is added up. A caller's total already contains its
    callees', so a sum of totals would count the same nanosecond once
    per stack frame.

    Attributes:
        label: What the group is called.
        calls: How often anything in it was entered.
        self_nanoseconds: Host time spent inside the group's own code.
        self_text: That time as it is shown.
        share: What part of the measured window it accounts for.
        children: Groups below this one, empty at the leaves.
        entry: The measurement, when the group is one function.
    """

    model_config = ConfigDict(frozen=True)

    label: str
    calls: int = 0
    self_nanoseconds: int = 0
    self_text: str = ""
    share: float = 0.0
    children: tuple[ProfileGroupView, ...] = ()
    entry: ProfileEntryView | None = None

    @property
    def share_text(self) -> str:
        """The share as a percentage, as a column shows it."""
        return f"{self.share * 100:.1f}%"


class ProfileView(BaseModel):
    """Everything one window of profiling measured.

    Attributes:
        groups: Origin, then directory, then function; heaviest first.
        heaviest: The functions that spent the most time in themselves.
        measured_nanoseconds: Host time the profile accounts for.
        measured_text: That time as it is shown.
        lost_functions: Measurements the simulation had no room for.
        is_profiling: Whether any instrumented function ran at all.
    """

    model_config = ConfigDict(frozen=True)

    groups: tuple[ProfileGroupView, ...] = ()
    heaviest: tuple[ProfileEntryView, ...] = ()
    measured_nanoseconds: int = 0
    measured_text: str = ""
    lost_functions: int = 0
    is_profiling: bool = False

    @property
    def function_count(self) -> int:
        """How many functions were measured."""
        return sum(len(directory.children) for group in self.groups for directory in group.children)

    @property
    def note(self) -> str:
        """What to say above the chart, including when there is nothing.

        A build without instrumentation and a window in which nothing ran
        look the same from here, and the same sentence answers both.
        """
        if not self.is_profiling:
            return (
                "Nothing instrumented ran. Build with profile = true in "
                "looper.toml to measure the firmware and the device model."
            )
        lost = f", {self.lost_functions} measurements dropped" if self.lost_functions else ""
        return f"{self.function_count} functions, {self.measured_text} accounted for{lost}"
