"""Declarator construction for generated C code."""

from __future__ import annotations

import pytest

from looper.infrastructure.codegen.c_naming import (
    declare,
    generated_source_name,
    hook_type_name,
)


@pytest.mark.parametrize(
    ("type_spelling", "expected"),
    [
        ("size_t", "size_t len"),
        ("uint8_t *", "uint8_t *len"),
        ("const uint8_t *", "const uint8_t *len"),
        ("adapter_spi_callback_t", "adapter_spi_callback_t len"),
    ],
)
def test_plain_types_put_the_name_last(type_spelling: str, expected: str) -> None:
    assert declare(type_spelling, "len") == expected


def test_a_function_pointer_puts_the_name_inside_the_parentheses() -> None:
    spelling = "void (*)(void *, _Bool)"

    assert declare(spelling, "callback") == "void (*callback)(void *, _Bool)"


def test_only_the_first_parenthesis_group_receives_the_name() -> None:
    spelling = "void (*)(void (*)(int))"

    assert declare(spelling, "cb") == "void (*cb)(void (*)(int))"


def test_hook_and_source_names_follow_the_declaration() -> None:
    assert hook_type_name("adapter_spi_transfer") == "looper_adapter_spi_transfer_hook_t"
    assert generated_source_name("adapter_spi_dma.h") == "sil_adapter_spi_dma.c"
