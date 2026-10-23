"""Result of comparing a parsed adapter surface against its contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique


@unique
class GapReason(Enum):
    """Why a declaration and its contract do not line up."""

    PARAMETER_NOT_CONTRACTED = "parameter_not_contracted"
    UNKNOWN_FUNCTION = "unknown_function"
    UNKNOWN_PARAMETER = "unknown_parameter"


@dataclass(frozen=True)
class ContractGap:
    """A single mismatch between declarations and contract.

    Attributes:
        function_name: Function the gap was found on.
        reason: Why the gap was reported.
        parameter_name: Parameter the gap was found on, if it is parameter level.
    """

    function_name: str
    reason: GapReason
    parameter_name: str | None = None


@dataclass(frozen=True)
class ContractCoverage:
    """The complete result of comparing a surface against a contract.

    Attributes:
        gaps: Every mismatch found, in surface order followed by contract order.
    """

    gaps: tuple[ContractGap, ...] = field(default_factory=tuple)

    @property
    def is_complete(self) -> bool:
        """Whether the contract matches the declarations exactly."""
        return not self.gaps

    @property
    def unspecified(self) -> tuple[ContractGap, ...]:
        """Parameters whose semantics are still missing.

        These are the gaps that make generation unsafe. A stale entry naming
        something the headers no longer declare is untidy, but it leaves
        nothing unspecified, so it is reported without blocking anything.
        """
        return self.gaps_with_reason(GapReason.PARAMETER_NOT_CONTRACTED)

    @property
    def stale(self) -> tuple[ContractGap, ...]:
        """Contract entries that no longer match any declaration."""
        return self.gaps_with_reason(GapReason.UNKNOWN_FUNCTION) + self.gaps_with_reason(
            GapReason.UNKNOWN_PARAMETER
        )

    @property
    def is_specified(self) -> bool:
        """Whether every parameter carrying memory has a contract."""
        return not self.unspecified

    def gaps_with_reason(self, reason: GapReason) -> tuple[ContractGap, ...]:
        """Every gap reported for the given reason."""
        return tuple(gap for gap in self.gaps if gap.reason is reason)

    @property
    def functions_with_gaps(self) -> tuple[str, ...]:
        """Names of the functions carrying at least one gap, without repeats."""
        return tuple(dict.fromkeys(gap.function_name for gap in self.gaps))
