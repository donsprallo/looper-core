"""Firmware variables and functions, as the debug information describes them."""

from __future__ import annotations

from looper.domain.model.firmware.bit_range import BitRange
from looper.domain.model.firmware.firmware_variable import FirmwareVariable
from looper.domain.model.firmware.function_symbol import FunctionSymbol
from looper.domain.model.firmware.loaded_image import LoadedImage
from looper.domain.model.firmware.static_symbol import StaticSymbol
from looper.domain.model.firmware.variable_encoding import VariableEncoding
from looper.domain.model.firmware.variable_origin import VariableOrigin
from looper.domain.model.firmware.variable_path import VariablePath
from looper.domain.model.firmware.variable_watch import VariableWatch

__all__ = [
    "BitRange",
    "FirmwareVariable",
    "FunctionSymbol",
    "LoadedImage",
    "StaticSymbol",
    "VariableEncoding",
    "VariableOrigin",
    "VariablePath",
    "VariableWatch",
]
