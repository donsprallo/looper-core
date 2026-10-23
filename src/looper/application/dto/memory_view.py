"""Data transfer objects describing where a simulation's memory goes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StaticObjectView(BaseModel):
    """One statically allocated object, ready to be printed.

    Attributes:
        name: Name the debug information gives it.
        origin: Which part of the simulation it belongs to.
        directory: Where its source lives.
        file_name: Its source file, without the path.
        bytes_used: Size of the whole object.
        size_text: That size as it is shown.
        is_constant: Whether it is read only.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    origin: str
    directory: str = ""
    file_name: str = ""
    bytes_used: int = 0
    size_text: str = ""
    is_constant: bool = False


class StaticMemoryView(BaseModel):
    """What a build holds before it runs.

    Attributes:
        biggest: The largest objects, which is where a budget goes.
        by_directory: What each source directory holds, heaviest first.
        object_count: How many objects were described.
        total_bytes: What all of them add up to.
        writable_bytes: What the ones that are not read only add up to.
        firmware_bytes: What the firmware's own writable objects cost.
        budget_bytes: What the project allows itself, zero for no limit.
        is_within_budget: Whether the writable bytes fit that limit.
        total_text: The total as it is shown.
        writable_text: The writable bytes as they are shown.
        firmware_text: The firmware's own bytes as they are shown.
    """

    model_config = ConfigDict(frozen=True)

    biggest: tuple[StaticObjectView, ...] = ()
    by_directory: tuple[tuple[str, str], ...] = ()
    object_count: int = 0
    total_bytes: int = 0
    writable_bytes: int = 0
    firmware_bytes: int = 0
    budget_bytes: int = 0
    is_within_budget: bool = True
    total_text: str = ""
    writable_text: str = ""
    firmware_text: str = ""

    @property
    def summary(self) -> str:
        """One line saying what is held and whether it fits.

        The firmware's own writable bytes come first, because that is
        the figure anyone is actually asking about. looper's recording
        rings are megabytes and are not on anybody's board, so leading
        with the total would bury the answer under the tool.
        """
        held = (
            f"{self.firmware_text} of writable static memory in the firmware "
            f"({self.writable_text} including looper's own, "
            f"{self.object_count} objects)"
        )
        if self.budget_bytes == 0:
            return held
        verdict = "within" if self.is_within_budget else "over"
        return f"{held}; {verdict} the budget of {self.budget_bytes} bytes"


class StackFrameView(BaseModel):
    """One function on the stack, ready to be printed.

    Attributes:
        function: Name the debug information gives it.
        origin: Which part of the simulation it belongs to.
        file_name: Its source file, without the path.
        bytes_used: Largest frame of it that was seen.
        size_text: That size as it is shown.
    """

    model_config = ConfigDict(frozen=True)

    function: str
    origin: str
    file_name: str = ""
    bytes_used: int = 0
    size_text: str = ""


class StackUsageView(BaseModel):
    """How deep the firmware went, and what it took with it.

    Attributes:
        path: The calls that were open at the deepest moment.
        largest: The functions that put the most on the stack.
        deepest_bytes: Host stack in use at that moment.
        deepest_depth: Frames on the stack at that moment.
        deepest_text: Those bytes as they are shown.
        path_is_complete: Whether the whole path was remembered.
        is_measured: Whether anything was measured at all.
    """

    model_config = ConfigDict(frozen=True)

    path: tuple[StackFrameView, ...] = ()
    largest: tuple[StackFrameView, ...] = ()
    deepest_bytes: int = 0
    deepest_depth: int = 0
    deepest_text: str = ""
    path_is_complete: bool = True
    is_measured: bool = False

    @property
    def summary(self) -> str:
        """One line saying how deep it went, or why nothing is known."""
        if not self.is_measured:
            return (
                "Nothing instrumented ran. Build with profile = true in "
                "looper.toml to measure the stack."
            )
        cut = "" if self.path_is_complete else ", path cut short"
        return f"deepest {self.deepest_text} over {self.deepest_depth} frames{cut}"


class AllocationSiteView(BaseModel):
    """One place that is holding something, ready to be printed.

    Attributes:
        function: Function the allocation was made from.
        origin: Which part of the simulation it belongs to.
        file_name: Its source file, without the path.
        blocks: Blocks from here that have not been freed.
        bytes_used: What those blocks add up to.
        size_text: That size as it is shown.
    """

    model_config = ConfigDict(frozen=True)

    function: str
    origin: str
    file_name: str = ""
    blocks: int = 0
    bytes_used: int = 0
    size_text: str = ""


class HeapUsageView(BaseModel):
    """What the firmware asked the allocator for.

    Attributes:
        outstanding: Where what is still out came from, heaviest first.
        allocations: Calls that returned a block.
        frees: Blocks given back.
        failures: Calls the allocator could not satisfy.
        live_text: What is out now, as it is shown.
        peak_text: The most that was ever out, as it is shown.
        firmware_text: What the firmware's own code still holds.
        untracked_blocks: Blocks freed that were never seen allocated.
        never_allocated: Whether nothing asked for anything.
        is_watched: Whether the allocator is wrapped in this build.
    """

    model_config = ConfigDict(frozen=True)

    outstanding: tuple[AllocationSiteView, ...] = ()
    allocations: int = 0
    frees: int = 0
    failures: int = 0
    live_text: str = ""
    peak_text: str = ""
    firmware_text: str = ""
    untracked_blocks: int = 0
    never_allocated: bool = False
    is_watched: bool = False

    @property
    def outstanding_blocks(self) -> int:
        """Blocks that have not been given back."""
        return sum(site.blocks for site in self.outstanding)

    @property
    def summary(self) -> str:
        """One line saying what passed through, or why nothing is known.

        "Nothing was allocated" is about the window, and a window that
        allocated nothing may still be holding what an earlier one did.
        Saying both is the difference between a report and a riddle.
        """
        if not self.is_watched:
            return (
                "The allocator is not being watched. Build with "
                "track_allocations = true in looper.toml to see it."
            )
        held = f"{self.live_text} still out from before" if self.outstanding else ""
        if self.never_allocated:
            return "; ".join(filter(None, ["nothing was allocated", held]))
        return (
            f"{self.allocations} allocations, {self.frees} freed, "
            f"{self.live_text} out now, {self.peak_text} at the peak"
        )


class MemoryView(BaseModel):
    """Where a simulation's memory goes, in the three places it can.

    Attributes:
        static: What the build holds before it runs.
        stack: How deep it went while it ran.
        heap: What it asked the allocator for.
    """

    model_config = ConfigDict(frozen=True)

    static: StaticMemoryView = StaticMemoryView()
    stack: StackUsageView = StackUsageView()
    heap: HeapUsageView = HeapUsageView()
