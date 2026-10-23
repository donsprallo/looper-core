"""Hand written semantics that the declarations alone cannot express."""

from __future__ import annotations

from looper.domain.model.contract.adapter_contract import AdapterContract
from looper.domain.model.contract.bus_role import BusRole, BusRoleKind
from looper.domain.model.contract.coverage import ContractCoverage, ContractGap, GapReason
from looper.domain.model.contract.function_contract import FunctionContract
from looper.domain.model.contract.parameter_contract import (
    BufferLifetime,
    ParameterContract,
    ParameterRole,
    WriteMoment,
)

__all__ = [
    "AdapterContract",
    "BufferLifetime",
    "BusRole",
    "BusRoleKind",
    "ContractCoverage",
    "ContractGap",
    "FunctionContract",
    "GapReason",
    "ParameterContract",
    "ParameterRole",
    "WriteMoment",
]
