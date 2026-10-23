"""Input and output of the simulation generation use case."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from pydantic import BaseModel, ConfigDict


class GenerateSimulationRequest(BaseModel):
    """What to generate, and where to put it.

    Attributes:
        header_directory: Directory holding the adapter headers.
        output_directory: Directory the generated files are written to.
        contract_path: Contract definition, or ``None`` to generate without one.
        allow_incomplete_contract: Whether generation proceeds although
            parameters still lack a contract.
    """

    model_config = ConfigDict(frozen=True)

    header_directory: Path
    output_directory: Path
    contract_path: Path | None = None
    allow_incomplete_contract: bool = False


class GeneratedFileSummary(BaseModel):
    """One file that generation produced.

    Attributes:
        relative_path: Path below the output directory.
        kind: Role the file plays in the simulation build.
        line_count: Number of lines written.
    """

    model_config = ConfigDict(frozen=True)

    relative_path: PurePosixPath
    kind: str
    line_count: int


class GenerateSimulationReport(BaseModel):
    """The result of generating a simulation.

    Attributes:
        output_directory: Directory the files were written to.
        files: One summary per generated file.
        function_count: Number of adapter functions that were simulated.
        uncontracted_count: Number of parameters generated with a default.
        stale_count: Number of contract entries that match no declaration.
    """

    model_config = ConfigDict(frozen=True)

    output_directory: Path
    files: tuple[GeneratedFileSummary, ...]
    function_count: int
    uncontracted_count: int
    stale_count: int = 0
