"""Declarations parsed from HAL adapter headers."""

from __future__ import annotations

from looper.domain.model.c_api.adapter_module import AdapterModule
from looper.domain.model.c_api.adapter_surface import AdapterSurface
from looper.domain.model.c_api.c_enum import CEnum, CEnumerator
from looper.domain.model.c_api.c_extern_data import CExternData
from looper.domain.model.c_api.c_function import CFunction
from looper.domain.model.c_api.c_parameter import CParameter
from looper.domain.model.c_api.c_record import CField, CRecord, RecordKind
from looper.domain.model.c_api.c_type import CType, CTypeKind

__all__ = [
    "AdapterModule",
    "AdapterSurface",
    "CEnum",
    "CEnumerator",
    "CExternData",
    "CField",
    "CFunction",
    "CParameter",
    "CRecord",
    "CType",
    "CTypeKind",
    "RecordKind",
]
