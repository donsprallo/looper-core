"""Behaviour of the adapter surface analysis use case."""

from __future__ import annotations

from pathlib import Path

import pytest

from looper.application.dto import AnalyzeAdapterSurfaceRequest
from looper.application.queries import AnalyzeAdapterSurface
from looper.domain.model.c_api import (
    AdapterModule,
    AdapterSurface,
    CExternData,
    CFunction,
    CParameter,
    CType,
    CTypeKind,
)
from looper.domain.model.contract import (
    AdapterContract,
    FunctionContract,
    ParameterContract,
    ParameterRole,
)
from looper.domain.repositories import AdapterContractRepository, AdapterSurfaceRepository

BOOLEAN = CType(spelling="bool", kind=CTypeKind.BOOLEAN)
BYTE = CType(spelling="uint8_t", kind=CTypeKind.INTEGER)
BYTE_POINTER = CType(spelling="uint8_t *", kind=CTypeKind.POINTER, pointee=BYTE)
RECORD = CType(spelling="demo_interface_t", kind=CTypeKind.RECORD, is_const=True)

TRANSFER = CFunction(
    name="adapter_demo_transfer",
    return_type=BOOLEAN,
    parameters=(CParameter("rx_data", BYTE_POINTER),),
)
SURFACE = AdapterSurface(
    modules=(
        AdapterModule(
            name="demo",
            header_path=Path("Inc/adapter_demo.h"),
            functions=(TRANSFER,),
            extern_data=(CExternData(name="demo_interface", type=RECORD),),
        ),
    )
)


class StubSurfaceRepository(AdapterSurfaceRepository):
    def __init__(self, surface: AdapterSurface) -> None:
        self.requested: Path | None = None
        self._surface = surface

    def load(self, header_directory: Path) -> AdapterSurface:
        self.requested = header_directory
        return self._surface


class StubContractRepository(AdapterContractRepository):
    def __init__(self, contract: AdapterContract) -> None:
        self.requested: Path | None = None
        self._contract = contract

    def load(self, contract_path: Path) -> AdapterContract:
        self.requested = contract_path
        return self._contract


@pytest.fixture
def contracts() -> StubContractRepository:
    return StubContractRepository(
        AdapterContract(
            functions=(
                FunctionContract(
                    function_name="adapter_demo_transfer",
                    parameters=(
                        ParameterContract(parameter_name="rx_data", role=ParameterRole.OUTPUT),
                    ),
                ),
            )
        )
    )


def test_the_report_counts_what_a_simulation_must_provide(
    contracts: StubContractRepository,
) -> None:
    use_case = AnalyzeAdapterSurface(StubSurfaceRepository(SURFACE), contracts)

    report = use_case.execute(
        AnalyzeAdapterSurfaceRequest(header_directory=Path("Inc"), contract_path=Path("c.toml"))
    )

    assert report.function_count == 1
    assert report.extern_data_count == 1
    assert report.modules[0].extern_data_names == ("demo_interface",)
    assert report.is_contract_complete


def test_without_a_contract_path_the_repository_is_not_consulted(
    contracts: StubContractRepository,
) -> None:
    use_case = AnalyzeAdapterSurface(StubSurfaceRepository(SURFACE), contracts)

    report = use_case.execute(AnalyzeAdapterSurfaceRequest(header_directory=Path("Inc")))

    assert contracts.requested is None
    assert [gap.parameter_name for gap in report.gaps] == ["rx_data"]


def test_the_requested_directory_reaches_the_repository(
    contracts: StubContractRepository,
) -> None:
    surfaces = StubSurfaceRepository(SURFACE)

    AnalyzeAdapterSurface(surfaces, contracts).execute(
        AnalyzeAdapterSurfaceRequest(header_directory=Path("Inc"))
    )

    assert surfaces.requested == Path("Inc")
