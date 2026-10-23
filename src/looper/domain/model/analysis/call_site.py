"""Where the firmware reaches the adapter, and with what.

A contract says what the adapter does with an argument. Whether that is
safe depends on what the caller passed, and the caller is the firmware.
A call site is the join between the two: one place the firmware reaches
the adapter, with enough about each argument to judge it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique

from looper.domain.model.analysis.finding import SourceLocation


@unique
class ArgumentStorage(Enum):
    """Where what an argument points at lives, for as long as it lives.

    Only the first of these is a problem, and only for a pointer the
    adapter keeps: a local stops existing when its function returns, and
    an adapter still holding it is reading somebody else's stack.
    """

    AUTOMATIC = "automatic"
    STATIC = "static"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CallArgument:
    """One argument of one call, as far as it can be judged.

    Attributes:
        parameter_name: Name the adapter declares for this position.
        spelling: What the caller wrote, for the report to quote.
        storage: Where what it points at lives.
    """

    parameter_name: str
    spelling: str
    storage: ArgumentStorage = ArgumentStorage.UNKNOWN


@dataclass(frozen=True)
class CallSite:
    """One place the firmware calls one adapter function.

    Attributes:
        function: Adapter function being called.
        location: Where the call is written.
        arguments: What was passed, in order.
        caller: Function the call is written inside, when it is known.
    """

    function: str
    location: SourceLocation
    arguments: tuple[CallArgument, ...] = field(default_factory=tuple)
    caller: str = ""

    def argument(self, parameter_name: str) -> CallArgument | None:
        """The argument passed for one parameter, if it was passed at all."""
        for argument in self.arguments:
            if argument.parameter_name == parameter_name:
                return argument
        return None
