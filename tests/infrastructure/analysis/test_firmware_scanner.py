"""Reading real firmware sources with the libclang front end.

What the scanner has to get right is not finding a call -- that is easy
-- but telling apart things that look alike: a local from a static, a
field that happens to share a name with a function, installing a hook
from calling through one.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from looper.domain.model.analysis import ArgumentStorage
from looper.infrastructure.analysis import FirmwareScan, FirmwareScanner
from looper.infrastructure.parsing import ParseOptions

ADAPTER_HEADER = """
#ifndef ADAPTER_DEMO_H
#define ADAPTER_DEMO_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef struct { int pin; } demo_pin_t;
typedef bool (*looper_adapter_demo_transfer_hook_t)(void *, uint8_t *, size_t);
typedef void (*looper_adapter_demo_reset_hook_t)(void *);

typedef struct {
    looper_adapter_demo_transfer_hook_t adapter_demo_transfer;
    looper_adapter_demo_reset_hook_t adapter_demo_reset;
} looper_hooks_t;

typedef struct {
    void (*delay_us)(uint32_t us);
} demo_platform_t;

bool adapter_demo_transfer(void *context, uint8_t *rx_data, size_t len);
void adapter_demo_reset(void *context);
void delay_us(uint32_t us);
#endif
"""

FIRMWARE_SOURCE = """
#include "adapter_demo.h"

static uint8_t kept_buffer[8];

bool read_into_a_local(void *context)
{
    uint8_t frame[8];
    return adapter_demo_transfer(context, frame, sizeof frame);
}

bool read_into_a_static(void *context)
{
    return adapter_demo_transfer(context, kept_buffer, sizeof kept_buffer);
}

void wait(const demo_platform_t *platform)
{
    platform->delay_us(10);
}
"""

MODEL_SOURCE = """
#include "adapter_demo.h"

static bool model_transfer(void *context, uint8_t *rx_data, size_t len)
{
    (void)context;
    (void)rx_data;
    (void)len;
    return true;
}

void install(looper_hooks_t *hooks)
{
    if (hooks->adapter_demo_reset == 0) {
        hooks->adapter_demo_transfer = model_transfer;
    }
}
"""

WANTED = frozenset({"adapter_demo_transfer", "adapter_demo_reset", "delay_us"})


@pytest.fixture
def scan(tmp_path: Path) -> FirmwareScan:
    """One scan of a project holding a firmware and a device model."""
    (tmp_path / "adapter_demo.h").write_text(ADAPTER_HEADER, encoding="utf-8")
    firmware = tmp_path / "firmware.c"
    firmware.write_text(FIRMWARE_SOURCE, encoding="utf-8")
    model = tmp_path / "model.c"
    model.write_text(MODEL_SOURCE, encoding="utf-8")
    options = ParseOptions(include_directories=(tmp_path,))
    return FirmwareScanner(options).scan((firmware, model), WANTED)


def test_every_source_is_read(scan: FirmwareScan) -> None:
    assert (scan.units_read, scan.units_unreadable) == (2, 0)


def test_a_call_is_recorded_where_it_is_written(scan: FirmwareScan) -> None:
    site = scan.calls_to("adapter_demo_transfer")[0]

    assert site.caller == "read_into_a_local"
    assert site.location.path.name == "firmware.c"


def test_arguments_carry_the_names_the_adapter_declares(scan: FirmwareScan) -> None:
    site = scan.calls_to("adapter_demo_transfer")[0]

    assert [argument.parameter_name for argument in site.arguments] == [
        "context",
        "rx_data",
        "len",
    ]


def test_a_local_buffer_is_told_apart_from_a_static_one(scan: FirmwareScan) -> None:
    into_a_local, into_a_static = scan.calls_to("adapter_demo_transfer")

    assert into_a_local.argument("rx_data") is not None
    assert into_a_local.argument("rx_data").storage is ArgumentStorage.AUTOMATIC  # type: ignore[union-attr]
    assert into_a_static.argument("rx_data").storage is ArgumentStorage.STATIC  # type: ignore[union-attr]


def test_a_call_through_a_field_is_not_a_call_to_the_function_of_that_name(
    scan: FirmwareScan,
) -> None:
    """``platform->delay_us(10)`` reaches a pointer, not ``delay_us``."""
    assert scan.calls_to("delay_us") == ()
    assert "delay_us" not in scan.reached_functions


def test_installing_a_hook_counts_as_answering_the_call(scan: FirmwareScan) -> None:
    assert "adapter_demo_transfer" in scan.hooked_functions


def test_reading_a_hook_field_is_not_installing_one(scan: FirmwareScan) -> None:
    """Every generated adapter reads the table on every call it makes."""
    assert scan.hooked_functions == frozenset({"adapter_demo_transfer"})


def test_a_declared_function_nothing_names_is_absent_from_what_was_reached(
    scan: FirmwareScan,
) -> None:
    assert "adapter_demo_reset" not in scan.reached_functions


def test_a_source_that_cannot_be_read_is_counted_rather_than_hidden(
    tmp_path: Path,
) -> None:
    broken = tmp_path / "broken.c"
    broken.write_text('#include "nothing_here.h"\n', encoding="utf-8")

    scan = FirmwareScanner(ParseOptions()).scan((broken,), WANTED)

    assert (scan.units_read, scan.units_unreadable) == (0, 1)
