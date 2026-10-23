"""Invariants that span more than one adapter module."""

from __future__ import annotations

from pathlib import Path

import pytest

from looper.domain.model.c_api import AdapterModule, AdapterSurface, CFunction, CType, CTypeKind

VOID = CType(spelling="void", kind=CTypeKind.VOID)


def _module(name: str, function_name: str) -> AdapterModule:
    return AdapterModule(
        name=name,
        header_path=Path(f"Inc/adapter_{name}.h"),
        functions=(CFunction(name=function_name, return_type=VOID),),
    )


def test_colliding_function_names_across_modules_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate names: adapter_init"):
        AdapterSurface(modules=(_module("gpio", "adapter_init"), _module("spi", "adapter_init")))


def test_the_surface_flattens_functions_of_every_module() -> None:
    surface = AdapterSurface(
        modules=(_module("gpio", "adapter_gpio_set"), _module("spi", "adapter_spi_transfer"))
    )

    assert surface.module_names == ("gpio", "spi")
    assert [function.name for function in surface.functions] == [
        "adapter_gpio_set",
        "adapter_spi_transfer",
    ]
