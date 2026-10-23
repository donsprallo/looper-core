"""Rendering of the generated simulation sources."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

import pytest

from looper.domain.model.c_api import (
    AdapterModule,
    AdapterSurface,
    CExternData,
    CFunction,
    CParameter,
    CType,
    CTypeKind,
)
from looper.domain.model.codegen import GeneratedArtifact
from looper.domain.model.contract import (
    AdapterContract,
    FunctionContract,
    ParameterContract,
    ParameterRole,
    WriteMoment,
)
from looper.infrastructure.codegen import CSimulationGenerator

VOID = CType(spelling="void", kind=CTypeKind.VOID)
BOOLEAN = CType(spelling="bool", kind=CTypeKind.BOOLEAN)
FRAME = CType(spelling="demo_frame_t", kind=CTypeKind.RECORD)
FRAME_POINTER = CType(spelling="demo_frame_t *", kind=CTypeKind.POINTER, pointee=FRAME)
CALLBACK = CType(spelling="void (*)(void *, _Bool)", kind=CTypeKind.FUNCTION_POINTER)
INTERFACE = CType(spelling="const demo_interface_t", kind=CTypeKind.RECORD, is_const=True)

RECEIVE = CFunction(
    name="adapter_demo_receive",
    return_type=BOOLEAN,
    parameters=(CParameter("frame", FRAME_POINTER), CParameter("callback", CALLBACK)),
)
RESET = CFunction(name="adapter_demo_reset", return_type=VOID)

SURFACE = AdapterSurface(
    modules=(
        AdapterModule(
            name="demo",
            header_path=Path("Inc/adapter_demo.h"),
            functions=(RECEIVE, RESET),
            extern_data=(CExternData(name="demo_interface", type=INTERFACE),),
        ),
    )
)
CONTRACT = AdapterContract(
    functions=(
        FunctionContract(
            function_name="adapter_demo_receive",
            parameters=(
                ParameterContract(
                    parameter_name="frame",
                    role=ParameterRole.OUTPUT,
                    written_at=WriteMoment.ON_RETURN,
                ),
                ParameterContract(parameter_name="callback", role=ParameterRole.CALLBACK),
            ),
        ),
    )
)


@pytest.fixture
def artifacts() -> dict[str, GeneratedArtifact]:
    generated = CSimulationGenerator().generate(SURFACE, CONTRACT)
    return {str(artifact.relative_path): artifact for artifact in generated}


def test_every_module_becomes_one_source_file(
    artifacts: dict[str, GeneratedArtifact],
) -> None:
    assert set(artifacts) == {"looper_hooks.h", "looper_hooks.c", "sil_adapter_demo.c"}
    assert artifacts["sil_adapter_demo.c"].relative_path == PurePosixPath("sil_adapter_demo.c")


def test_a_function_pointer_parameter_is_declared_correctly(
    artifacts: dict[str, GeneratedArtifact],
) -> None:
    header = artifacts["looper_hooks.h"].content

    assert "void (*callback)(void *, _Bool)" in header
    assert "(*)(void *, _Bool) callback" not in header


def test_the_contract_reaches_the_generated_documentation(
    artifacts: dict[str, GeneratedArtifact],
) -> None:
    header = artifacts["looper_hooks.h"].content

    assert "@param frame: output, written on_return" in header
    assert "@param callback: callback" in header


def test_an_output_parameter_is_zeroed_when_no_hook_is_installed(
    artifacts: dict[str, GeneratedArtifact],
) -> None:
    source = artifacts["sil_adapter_demo.c"].content

    assert "if (frame != NULL) {" in source
    assert "*frame = (demo_frame_t){0};" in source


def test_a_void_function_forwards_without_returning_a_value(
    artifacts: dict[str, GeneratedArtifact],
) -> None:
    source = artifacts["sil_adapter_demo.c"].content

    assert "looper_table->adapter_demo_reset();" in source
    assert "void adapter_demo_reset(void)" in source


def test_an_exported_symbol_is_defined_with_an_override_macro(
    artifacts: dict[str, GeneratedArtifact],
) -> None:
    source = artifacts["sil_adapter_demo.c"].content

    assert "#ifndef LOOPER_INIT_demo_interface" in source
    assert "const demo_interface_t demo_interface = LOOPER_INIT_demo_interface;" in source


def test_without_a_contract_no_output_is_zeroed() -> None:
    generated = CSimulationGenerator().generate(SURFACE, AdapterContract())

    source = next(a for a in generated if str(a.relative_path) == "sil_adapter_demo.c")
    assert "*frame = " not in source.content
    assert "Contract:" not in source.content
