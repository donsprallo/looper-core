"""How a project actually uses the adapter it declares.

A surface says what the adapter offers and a contract says what each
part means. Neither says whether the firmware ever asks for it, or what
it passes when it does. That is what reading the project's own sources
adds, and it is the third thing the checks need.

Nothing here knows how the reading was done. A scan of C sources fills
it today; anything that can answer the same questions would do.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from looper.domain.model.analysis.call_site import CallSite


@dataclass(frozen=True)
class FirmwareUsage:
    """What a project does with its adapter, as far as its sources say.

    Attributes:
        call_sites: Every place an adapter function is called by name.
        reached_functions: Functions the project names at all, whether it
            calls them or stores them in a table of function pointers.
        answered_functions: Functions a device model stands behind, by
            having installed a hook for them.
        initialised_data: Exported data symbols the build gives a value.
        units_read: Translation units that could be read.
        units_unreadable: Translation units that could not.
    """

    call_sites: tuple[CallSite, ...] = field(default_factory=tuple)
    reached_functions: frozenset[str] = frozenset()
    answered_functions: frozenset[str] = frozenset()
    initialised_data: frozenset[str] = frozenset()
    units_read: int = 0
    units_unreadable: int = 0

    def __post_init__(self) -> None:
        if self.units_read < 0 or self.units_unreadable < 0:
            raise ValueError("A count of translation units is never negative")

    def reaches(self, function_name: str) -> bool:
        """Whether the project names a function at all."""
        return function_name in self.reached_functions

    def answers(self, function_name: str) -> bool:
        """Whether something stands behind a function when it is called."""
        return function_name in self.answered_functions
