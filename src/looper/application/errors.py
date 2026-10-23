"""Failures raised by the use cases."""

from __future__ import annotations

from looper.domain.model.contract import ContractCoverage

MAXIMUM_LISTED_GAPS = 10
NEWLINE = "\n"


class ContractIncompleteError(RuntimeError):
    """Generation was requested while parameters still lack a contract.

    Generating from an incomplete contract produces a simulation that compiles
    and behaves plausibly while treating borrowed buffers as copied. The use
    case refuses instead, unless the caller explicitly accepts the defaults.

    Attributes:
        coverage: The gaps that caused the refusal.
    """

    def __init__(self, coverage: ContractCoverage) -> None:
        self.coverage = coverage
        super().__init__(self._describe())

    def _describe(self) -> str:
        """Build a message naming the first few gaps and their total count."""
        listed = self.coverage.unspecified[:MAXIMUM_LISTED_GAPS]
        details = "\n".join(f"  {_render(gap.function_name, gap.parameter_name)}" for gap in listed)
        remaining = len(self.coverage.unspecified) - len(listed)
        suffix = f"\n  ... and {remaining} more" if remaining > 0 else ""
        return (
            f"{len(self.coverage.unspecified)} declarations have no contract:\n{details}{suffix}\n"
            "Add them, or pass --allow-incomplete-contract to accept the defaults."
        )


def _render(function_name: str, parameter_name: str | None) -> str:
    """Render one gap as ``function.parameter``."""
    if parameter_name is None:
        return function_name
    return f"{function_name}.{parameter_name}"


class SimulationBuildFailedError(RuntimeError):
    """The compiler rejected the generated simulation.

    Attributes:
        compiler: Compiler that was invoked.
        diagnostics: What the compiler reported.
    """

    def __init__(self, compiler: str, diagnostics: str) -> None:
        self.compiler = compiler
        self.diagnostics = diagnostics
        summary = f"{compiler} failed to build the simulation:"
        super().__init__(NEWLINE.join((summary, diagnostics)))


class DebugInformationUnavailableError(RuntimeError):
    """The firmware variables of the running simulation cannot be read.

    Either the simulation could not say which executable it is running, or
    that executable carries no debug information. Both mean the same thing to
    a client: there is no list of variables to offer.
    """


class VariableWriteRejectedError(ValueError):
    """A write was refused before it was sent.

    The simulation refuses the same writes, but it can only do so after a
    round trip and it answers in terms of a channel number. Refusing here
    lets a client say which variable and why.

    Attributes:
        path: Variable the write was aimed at.
    """

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        super().__init__(f"{path}: {reason}")
