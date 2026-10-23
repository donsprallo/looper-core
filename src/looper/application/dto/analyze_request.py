"""Input of the adapter surface analysis use case."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class AnalyzeAdapterSurfaceRequest(BaseModel):
    """What to analyse.

    How the headers are parsed is not part of this request. Compiler arguments
    belong to the repository implementation, so that the use case stays
    independent of the front end that reads the headers.

    Attributes:
        header_directory: Directory holding the adapter headers.
        contract_path: Contract definition, or ``None`` to analyse without one.
    """

    model_config = ConfigDict(frozen=True)

    header_directory: Path
    contract_path: Path | None = None
