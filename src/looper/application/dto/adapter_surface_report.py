"""Data transfer objects describing an analysed adapter surface."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class ModuleSummary(BaseModel):
    """What one adapter header contributes to the surface.

    Attributes:
        name: Short module name such as ``gpio``.
        header_path: Header the declarations were read from.
        function_count: Number of public functions.
        record_count: Number of structs and unions.
        enum_count: Number of enumerations.
        extern_data_names: Exported data symbols the simulation must define.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    header_path: Path
    function_count: int
    record_count: int
    enum_count: int
    extern_data_names: tuple[str, ...]


class ContractGapSummary(BaseModel):
    """One parameter or function whose semantics are not pinned down.

    Attributes:
        function_name: Function the gap was found on.
        reason: Why the gap was reported.
        parameter_name: Parameter the gap was found on, if it is parameter level.
    """

    model_config = ConfigDict(frozen=True)

    function_name: str
    reason: str
    parameter_name: str | None = None


class AdapterSurfaceReport(BaseModel):
    """The result of analysing an adapter header directory.

    Attributes:
        header_directory: Directory the headers were read from.
        modules: One summary per parsed header.
        gaps: Every parameter still missing an explicit contract.
    """

    model_config = ConfigDict(frozen=True)

    header_directory: Path
    modules: tuple[ModuleSummary, ...]
    gaps: tuple[ContractGapSummary, ...]

    @property
    def function_count(self) -> int:
        """Total number of functions the simulation has to implement."""
        return sum(module.function_count for module in self.modules)

    @property
    def extern_data_count(self) -> int:
        """Total number of data symbols the simulation has to define."""
        return sum(len(module.extern_data_names) for module in self.modules)

    @property
    def is_contract_complete(self) -> bool:
        """Whether every parameter carrying memory has an explicit contract."""
        return not self.gaps
