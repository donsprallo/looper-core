"""Result of compiling a simulation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BuildOutcome:
    """What a compiler run produced.

    Attributes:
        executable: Path the executable was written to.
        succeeded: Whether the compiler reported success.
        compiler: Compiler that was invoked.
        diagnostics: Compiler output, empty when the run was silent.
        unit_count: Translation units the build is made of. Zero when
            whatever built it does not count them.
        recompiled_count: How many of them this build had to compile
            again. Fewer than all means the rest were still good.
    """

    executable: Path
    succeeded: bool
    compiler: str
    diagnostics: str = ""
    unit_count: int = 0
    recompiled_count: int = 0

    def __post_init__(self) -> None:
        if self.unit_count < 0 or self.recompiled_count < 0:
            raise ValueError("A count of translation units is never negative")
        if self.recompiled_count > self.unit_count:
            raise ValueError("A build cannot recompile more units than it has")
