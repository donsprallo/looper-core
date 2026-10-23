"""Behaviour of the adapter module naming service."""

from __future__ import annotations

from pathlib import Path

import pytest

from looper.domain.services import module_name_from_header


def test_the_adapter_prefix_is_stripped() -> None:
    assert module_name_from_header(Path("Inc/adapter_spi_dma.h")) == "spi_dma"


def test_an_unexpected_name_keeps_its_full_stem() -> None:
    assert module_name_from_header(Path("Inc/embd_gpio.h")) == "embd_gpio"


def test_a_source_file_is_rejected() -> None:
    with pytest.raises(ValueError, match="not a C header file"):
        module_name_from_header(Path("Src/adapter_spi.c"))
