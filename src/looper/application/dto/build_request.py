"""Input and output of the build and run use cases."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class BuildSimulationRequest(BaseModel):
    """What to build.

    Attributes:
        definition_path: Path of the build definition.
        allow_incomplete_contract: Whether generation proceeds although
            parameters still lack a contract.
    """

    model_config = ConfigDict(frozen=True)

    definition_path: Path
    allow_incomplete_contract: bool = False


class RunSimulationRequest(BaseModel):
    """What to build and run.

    Attributes:
        definition_path: Path of the build definition.
        port: Port the simulation should listen on.
        virtual_time: Whether the simulation runs on a virtual clock.
        skip_build: Whether an existing executable is started unchanged.
        allow_incomplete_contract: Whether generation proceeds although
            parameters still lack a contract.
    """

    model_config = ConfigDict(frozen=True)

    definition_path: Path
    port: int | None = None
    virtual_time: bool = False
    skip_build: bool = False
    allow_incomplete_contract: bool = False


class BuildSimulationReport(BaseModel):
    """The result of building a simulation.

    Attributes:
        name: Name of the simulation.
        executable: Path of the executable that was produced.
        compiler: Compiler that was invoked.
        generated_file_count: Number of generated source files.
        function_count: Number of adapter functions that were simulated.
        uncontracted_count: Number of parameters generated with a default.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    executable: Path
    compiler: str
    generated_file_count: int
    function_count: int
    uncontracted_count: int
