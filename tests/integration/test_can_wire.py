"""The byte layout of a CAN frame, checked against the C that writes it.

A wire format is only a format if both ends agree, and the two ends here
are a C encoder and whatever reads it. So the C is compiled and asked,
rather than a Python copy of it being asked about itself.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest
from bridge_fixture import compiler_on_path

from looper.infrastructure.build.project_sources import runtime_units
from looper.infrastructure.runtime_location import runtime_include_directories

PROBE = """
/* Encode a few frames and print the bytes, so a test can read them. */
#include <stdio.h>

#include "looper_can_wire.h"

static void show(const char *name, const looper_can_frame_t *frame)
{
    uint8_t buffer[LOOPER_CAN_WIRE_CAPACITY];
    const size_t length = looper_can_wire_encode(frame, buffer, sizeof(buffer));

    printf("  \\"%s\\": \\"", name);
    for (size_t index = 0u; index < length; index++) {
        printf("%02x", buffer[index]);
    }
    printf("\\"%s\\n", length > 0u ? "," : ",");
}

int main(void)
{
    looper_can_frame_t standard = {.id = 0x123u, .extended = false, .length = 2u};
    looper_can_frame_t extended = {.id = 0x1ABCDEu, .extended = true, .length = 0u};
    looper_can_frame_t full = {.id = 0x7FFu, .extended = false, .length = 8u};
    looper_can_frame_t decoded;
    uint8_t three[3] = {0u, 0u, 0u};

    standard.payload[0] = 0xAAu;
    standard.payload[1] = 0xBBu;
    for (uint8_t index = 0u; index < 8u; index++) {
        full.payload[index] = index;
    }
    printf("{\\n");
    show("standard", &standard);
    show("extended", &extended);
    show("full", &full);
    printf("  \\"short_is_refused\\": %zu,\\n",
           looper_can_wire_decode(three, sizeof(three), &decoded));
    printf("  \\"capacity\\": %u\\n}\\n", (unsigned)LOOPER_CAN_WIRE_CAPACITY);
    return 0;
}
"""


@pytest.fixture(scope="module")
def encoded(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    """What the C encoder makes of a few frames."""
    compiler = compiler_on_path()
    if compiler is None:
        pytest.skip("no C compiler on PATH")
    directory = tmp_path_factory.mktemp("wire")
    source = directory / "wire_probe.c"
    source.write_text(PROBE, encoding="utf-8")
    executable = directory / ("wire.exe" if sys.platform == "win32" else "wire")
    built = subprocess.run(  # noqa: S603
        [
            compiler,
            "-std=c11",
            "-O1",
            str(source),
            *(str(one) for one in runtime_units()),
            "-o",
            str(executable),
            *(f"-I{one}" for one in runtime_include_directories()),
            "-lws2_32" if sys.platform == "win32" else "-lm",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert built.returncode == 0, built.stderr or built.stdout
    reported = subprocess.run(  # noqa: S603
        [str(executable)], capture_output=True, text=True, check=True
    )
    return dict(json.loads(reported.stdout))


def test_a_standard_frame_is_identifier_flags_length_payload(
    encoded: dict[str, object],
) -> None:
    assert encoded["standard"] == "2301000000" + "02" + "aabb"


def test_an_extended_frame_says_so_in_its_flags(encoded: dict[str, object]) -> None:
    assert encoded["extended"] == "debc1a00" + "01" + "00"


def test_a_full_payload_fits_the_stated_capacity(encoded: dict[str, object]) -> None:
    assert encoded["full"] == "ff070000" + "00" + "08" + "0001020304050607"
    assert len(str(encoded["full"])) // 2 == encoded["capacity"]


def test_bytes_that_are_not_yet_a_frame_decode_to_nothing(
    encoded: dict[str, object],
) -> None:
    """A stream hands over half a frame all the time; it is not an error."""
    assert encoded["short_is_refused"] == 0
