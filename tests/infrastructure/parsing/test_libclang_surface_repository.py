"""Parsing of real header files with the libclang front end."""

from __future__ import annotations

from pathlib import Path

import pytest

from looper.domain.model.c_api import CTypeKind
from looper.infrastructure.parsing import (
    HeaderParseError,
    LibclangAdapterSurfaceRepository,
    ParseOptions,
)

ADAPTER_HEADER = """
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef void (*adapter_demo_callback_t)(void *ctx, bool success);

typedef enum {
    DEMO_STATE_READY,
    DEMO_STATE_BUSY
} demo_state_t;

typedef struct {
    uint8_t buffer[32];
    demo_state_t state;
} demo_context_t;

typedef struct {
    uint32_t pin;
} demo_pin_t;

extern const demo_pin_t demo_pin_interface;

static int adapter_demo_internal(void);

bool adapter_demo_transfer(
    void *context,
    const uint8_t *tx_data,
    uint8_t *rx_data,
    size_t len,
    adapter_demo_callback_t callback
);

void adapter_demo_reset(demo_context_t *context);
"""


@pytest.fixture
def header_directory(tmp_path: Path) -> Path:
    (tmp_path / "adapter_demo.h").write_text(ADAPTER_HEADER, encoding="utf-8")
    return tmp_path


def _load(directory: Path) -> object:
    return LibclangAdapterSurfaceRepository(ParseOptions()).load(directory)


def test_the_module_is_named_after_its_header(header_directory: Path) -> None:
    surface = _load(header_directory)

    assert surface.module_names == ("demo",)


def test_internal_linkage_is_not_part_of_the_surface(header_directory: Path) -> None:
    surface = _load(header_directory)

    assert "adapter_demo_internal" not in [function.name for function in surface.functions]


def test_exported_data_symbols_are_collected(header_directory: Path) -> None:
    surface = _load(header_directory)

    assert [symbol.name for symbol in surface.extern_data] == ["demo_pin_interface"]
    assert surface.extern_data[0].is_interface_table


def test_a_typedefed_function_pointer_is_recognised_as_a_callback(
    header_directory: Path,
) -> None:
    transfer = _load(header_directory).module("demo").function("adapter_demo_transfer")

    assert transfer.parameter("callback").is_callback
    assert transfer.parameter("callback").type.spelling == "adapter_demo_callback_t"


def test_pointer_roles_are_distinguished(header_directory: Path) -> None:
    transfer = _load(header_directory).module("demo").function("adapter_demo_transfer")

    assert transfer.parameter("context").is_context
    assert transfer.parameter("tx_data").is_buffer
    assert transfer.parameter("tx_data").type.points_to_const
    assert not transfer.parameter("rx_data").type.points_to_const


def test_an_anonymous_struct_is_named_after_its_typedef(header_directory: Path) -> None:
    module = _load(header_directory).module("demo")

    record = next(record for record in module.records if record.name == "demo_context_t")
    assert record.field_names == ("buffer", "state")
    assert record.fields[0].type.kind is CTypeKind.ARRAY
    assert record.fields[0].type.element_count == 32


def test_enumerator_values_are_resolved(header_directory: Path) -> None:
    module = _load(header_directory).module("demo")

    demo_state = next(enum for enum in module.enums if enum.name == "demo_state_t")
    assert [(e.name, e.value) for e in demo_state.enumerators] == [
        ("DEMO_STATE_READY", 0),
        ("DEMO_STATE_BUSY", 1),
    ]


def test_a_compiler_error_names_the_header(tmp_path: Path) -> None:
    (tmp_path / "adapter_broken.h").write_text("void f(undefined_type_t x);", encoding="utf-8")

    with pytest.raises(HeaderParseError, match="adapter_broken.h"):
        _load(tmp_path)


def test_a_missing_directory_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        _load(tmp_path / "absent")
