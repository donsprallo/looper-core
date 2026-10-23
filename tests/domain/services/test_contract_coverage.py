"""Behaviour of the contract coverage service."""

from __future__ import annotations

from pathlib import Path

from looper.domain.model.c_api import (
    AdapterModule,
    AdapterSurface,
    CFunction,
    CParameter,
    CType,
    CTypeKind,
)
from looper.domain.model.contract import (
    AdapterContract,
    BufferLifetime,
    FunctionContract,
    GapReason,
    ParameterContract,
    ParameterRole,
)
from looper.domain.services import evaluate_contract_coverage

BOOLEAN = CType(spelling="bool", kind=CTypeKind.BOOLEAN)
VOID = CType(spelling="void", kind=CTypeKind.VOID)
BYTE = CType(spelling="const uint8_t", kind=CTypeKind.INTEGER, is_const=True)
BYTE_POINTER = CType(spelling="const uint8_t *", kind=CTypeKind.POINTER, pointee=BYTE)
VOID_POINTER = CType(spelling="void *", kind=CTypeKind.POINTER, pointee=VOID)

TX_BEGIN = CFunction(
    name="adapter_can_payload_tx_begin",
    return_type=BOOLEAN,
    parameters=(CParameter("context", VOID_POINTER), CParameter("data", BYTE_POINTER)),
)
PANIC = CFunction(name="panic", return_type=VOID)


def _surface(*functions: CFunction) -> AdapterSurface:
    module = AdapterModule(name="can", header_path=Path("Inc/adapter_can.h"), functions=functions)
    return AdapterSurface(modules=(module,))


def test_an_uncontracted_function_reports_each_parameter_that_needs_one() -> None:
    coverage = evaluate_contract_coverage(_surface(TX_BEGIN), AdapterContract())

    gaps = coverage.gaps_with_reason(GapReason.PARAMETER_NOT_CONTRACTED)
    assert [gap.parameter_name for gap in gaps] == ["data"]
    assert coverage.functions_with_gaps == ("adapter_can_payload_tx_begin",)


def test_a_function_without_memory_parameters_needs_no_contract() -> None:
    coverage = evaluate_contract_coverage(_surface(PANIC), AdapterContract())

    assert coverage.is_complete


def test_an_opaque_context_does_not_require_a_contract() -> None:
    contract = AdapterContract(
        functions=(
            FunctionContract(
                function_name="adapter_can_payload_tx_begin",
                parameters=(
                    ParameterContract(
                        parameter_name="data",
                        role=ParameterRole.INPUT,
                        lifetime=BufferLifetime.BORROWED,
                    ),
                ),
            ),
        )
    )

    coverage = evaluate_contract_coverage(_surface(TX_BEGIN), contract)

    assert coverage.is_complete


def test_a_contract_naming_an_unknown_function_is_reported() -> None:
    contract = AdapterContract(functions=(FunctionContract(function_name="adapter_removed"),))

    coverage = evaluate_contract_coverage(_surface(PANIC), contract)

    gaps = coverage.gaps_with_reason(GapReason.UNKNOWN_FUNCTION)
    assert [gap.function_name for gap in gaps] == ["adapter_removed"]
