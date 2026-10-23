"""Everything one window of profiling measured, and how it adds up.

Only self time adds up. Totals do not: a caller's total already contains
its callees', so summing the totals of a firmware counts the same
nanosecond once per stack frame. Every rollup here is therefore a sum of
self times, which is the one number that answers "where did the second
go" without counting anything twice.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field

from looper.domain.model.profile.profiled_function import ProfiledFunction
from looper.domain.model.simulation.duration import (
    NANOSECONDS_PER_SECOND,
    duration_text,
)
from looper.domain.model.sources.function_origin import FunctionOrigin


@dataclass(frozen=True)
class ProfileGroup:
    """A set of measured functions, and what they cost together.

    Attributes:
        label: What the group is called, as a reader sees it.
        calls: How often anything in the group was entered.
        self_nanoseconds: Host time spent inside the group's own code.
        children: Groups below this one, empty at the leaves.
        function: The measurement, when the group is one function.
    """

    label: str
    calls: int = 0
    self_nanoseconds: int = 0
    children: tuple[ProfileGroup, ...] = field(default_factory=tuple)
    function: ProfiledFunction | None = None

    @property
    def display_self(self) -> str:
        """Host time in this group, as clients show it."""
        return duration_text(float(self.self_nanoseconds))

    @property
    def self_seconds(self) -> float:
        """Host time in this group, in seconds."""
        return self.self_nanoseconds / NANOSECONDS_PER_SECOND

    def share_of(self, measured_nanoseconds: int) -> float:
        """What part of a measured window this group accounts for."""
        if measured_nanoseconds <= 0:
            return 0.0
        return self.self_nanoseconds / measured_nanoseconds


@dataclass(frozen=True)
class ProfileReport:
    """What a window of profiling saw.

    Attributes:
        functions: Every function that ran, in no particular order.
        lost_functions: Functions the table had no room for. A profile
            that silently dropped the forty first function would put the
            missing time into nobody's column.
        instrumented_origins: Which parts of the simulation were woven
            with instrumentation at all, so that a reader knows an empty
            column means "not measured" rather than "took no time".
    """

    functions: tuple[ProfiledFunction, ...] = field(default_factory=tuple)
    lost_functions: int = 0
    instrumented_origins: frozenset[FunctionOrigin] = frozenset()

    def __post_init__(self) -> None:
        if self.lost_functions < 0:
            raise ValueError("A profile cannot have lost a negative number of functions")

    @property
    def measured_nanoseconds(self) -> int:
        """Host time the profile accounts for, counting nothing twice."""
        return sum(function.self_nanoseconds for function in self.functions)

    @property
    def is_empty(self) -> bool:
        """Whether nothing was measured, which usually means nothing was built for it."""
        return not self.functions

    def heaviest(self, count: int) -> tuple[ProfiledFunction, ...]:
        """The functions that spent the most time in themselves."""
        ordered = sorted(self.functions, key=lambda one: -one.self_nanoseconds)
        return tuple(ordered[:count])

    def by_origin(self) -> tuple[ProfileGroup, ...]:
        """One group per origin, heaviest first, split by directory below."""
        groups = [
            _group_of(origin.value, members, _by_directory(members))
            for origin, members in _split(self.functions, lambda one: one.origin).items()
        ]
        return _ordered(groups)


def _by_directory(functions: tuple[ProfiledFunction, ...]) -> tuple[ProfileGroup, ...]:
    """One group per source directory, each holding its functions."""
    groups = [
        _group_of(directory or "unknown source", members, _leaves(members))
        for directory, members in _split(functions, lambda one: one.directory).items()
    ]
    return _ordered(groups)


def _leaves(functions: tuple[ProfiledFunction, ...]) -> tuple[ProfileGroup, ...]:
    """One group per function, which is where the tree ends."""
    return _ordered(
        [
            ProfileGroup(
                label=function.name,
                calls=function.calls,
                self_nanoseconds=function.self_nanoseconds,
                function=function,
            )
            for function in functions
        ]
    )


def _group_of(
    label: str, members: tuple[ProfiledFunction, ...], children: tuple[ProfileGroup, ...]
) -> ProfileGroup:
    """Add a set of functions up into the group that holds them."""
    return ProfileGroup(
        label=label,
        calls=sum(member.calls for member in members),
        self_nanoseconds=sum(member.self_nanoseconds for member in members),
        children=children,
    )


def _ordered(groups: list[ProfileGroup]) -> tuple[ProfileGroup, ...]:
    """Heaviest first, and alphabetically where two weigh the same."""
    return tuple(sorted(groups, key=lambda one: (-one.self_nanoseconds, one.label)))


def _split[KeyT](
    functions: tuple[ProfiledFunction, ...], key: Callable[[ProfiledFunction], KeyT]
) -> dict[KeyT, tuple[ProfiledFunction, ...]]:
    """Gather functions under whatever the key says they belong to."""
    gathered: dict[KeyT, list[ProfiledFunction]] = defaultdict(list)
    for function in functions:
        gathered[key(function)].append(function)
    return {name: tuple(members) for name, members in gathered.items()}
