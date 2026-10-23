"""Domain service that compares an adapter surface against its contract."""

from __future__ import annotations

from looper.domain.model.c_api.adapter_surface import AdapterSurface
from looper.domain.model.c_api.c_function import CFunction
from looper.domain.model.c_api.c_parameter import CParameter
from looper.domain.model.contract.adapter_contract import AdapterContract
from looper.domain.model.contract.coverage import ContractCoverage, ContractGap, GapReason
from looper.domain.model.contract.function_contract import FunctionContract


def evaluate_contract_coverage(
    surface: AdapterSurface, contract: AdapterContract
) -> ContractCoverage:
    """Report every parameter whose semantics are not pinned down.

    Pointer parameters and callbacks cannot be simulated correctly from their
    declaration alone. Whether ``spi_context_t *context`` is an instance handle
    or a payload buffer, and whether a buffer may be retained after the call,
    is stated in the header documentation at best. This service names each one
    still missing a contract so that generation can fall back to a conservative
    default and say so, rather than guessing silently.

    Args:
        surface: Declarations parsed from the adapter headers.
        contract: Hand written semantics for those declarations.

    Returns:
        The gaps found in surface order, followed by stale contract entries.
    """
    gaps = [gap for function in surface.functions for gap in _gaps_of_function(function, contract)]
    gaps.extend(_stale_contract_gaps(surface, contract))
    return ContractCoverage(gaps=tuple(gaps))


def requires_contract(parameter: CParameter) -> bool:
    """Report whether a parameter carries semantics its declaration omits."""
    return parameter.is_buffer or parameter.is_callback


def _gaps_of_function(function: CFunction, contract: AdapterContract) -> list[ContractGap]:
    """Report every parameter of one function that still needs a contract."""
    function_contract = _contract_of(function, contract)
    return [
        ContractGap(function.name, GapReason.PARAMETER_NOT_CONTRACTED, parameter.name)
        for parameter in function.parameters
        if requires_contract(parameter) and not function_contract.covers(parameter.name)
    ]


def _contract_of(function: CFunction, contract: AdapterContract) -> FunctionContract:
    """Return the contract of a function, or an empty one when none exists."""
    if not contract.covers(function.name):
        return FunctionContract(function_name=function.name)
    return contract.function(function.name)


def _stale_contract_gaps(surface: AdapterSurface, contract: AdapterContract) -> list[ContractGap]:
    """Report contract entries that no longer match any declaration."""
    declared = {function.name: function for function in surface.functions}
    gaps: list[ContractGap] = []
    for function_contract in contract.functions:
        function = declared.get(function_contract.function_name)
        if function is None:
            gaps.append(ContractGap(function_contract.function_name, GapReason.UNKNOWN_FUNCTION))
            continue
        gaps.extend(_unknown_parameter_gaps(function, function_contract))
    return gaps


def _unknown_parameter_gaps(
    function: CFunction, function_contract: FunctionContract
) -> list[ContractGap]:
    """Report contract entries naming parameters the function does not declare."""
    return [
        ContractGap(function.name, GapReason.UNKNOWN_PARAMETER, name)
        for name in function_contract.contracted_parameter_names
        if not function.has_parameter(name)
    ]
