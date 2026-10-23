"""Whether an object's reported size is the one the compiler chose.

The sizes that matter to a memory budget are arrays: a buffer of
sixty four thousand samples is the thing that does not fit, and a
reader that followed the type chain would report it as one sample.
An array rarely carries a size of its own -- it carries an element
type and a subrange per dimension -- so the arithmetic is checked
here against a program that declares its own answer.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from bridge_fixture import compiler_on_path

from looper.infrastructure.debug import DwarfDebugReader

FIXTURE = """
/* Objects whose sizes a test can check against sizeof. */
#include <stdio.h>
#include <stdint.h>

typedef struct { uint32_t channel; uint64_t microseconds; double value; } sample_t;

uint8_t g_bytes[2048];
sample_t g_samples[4096];
uint16_t g_grid[8][16];
const uint32_t g_table[64] = {0};
double g_one;
sample_t g_single;

int main(void)
{
    printf("{\\"g_bytes\\": %zu, \\"g_samples\\": %zu, \\"g_grid\\": %zu,"
           " \\"g_table\\": %zu, \\"g_one\\": %zu, \\"g_single\\": %zu}\\n",
           sizeof(g_bytes), sizeof(g_samples), sizeof(g_grid),
           sizeof(g_table), sizeof(g_one), sizeof(g_single));
    return 0;
}
"""


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The fixture, compiled with debug information."""
    compiler = compiler_on_path()
    if compiler is None:
        pytest.skip("no C compiler on PATH")
    directory = tmp_path_factory.mktemp("statics")
    source = directory / "sizes.c"
    source.write_text(FIXTURE, encoding="utf-8")
    executable = directory / ("sizes.exe" if sys.platform == "win32" else "sizes")
    compiled = subprocess.run(  # noqa: S603
        [compiler, "-std=c11", "-g", "-O1", str(source), "-o", str(executable)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert compiled.returncode == 0, compiled.stderr or compiled.stdout
    return executable


@pytest.fixture(scope="module")
def symbols(built: Path) -> dict[str, bool]:
    """Which objects the reader considers read only."""
    return {one.name: one.is_constant for one in DwarfDebugReader().read_statics(built)}


@pytest.fixture(scope="module")
def sizes(built: Path) -> tuple[dict[str, int], dict[str, int]]:
    """What the compiler says, and what the reader says."""
    reported = subprocess.run(  # noqa: S603
        [str(built)], capture_output=True, text=True, check=True
    )
    declared = dict(json.loads(reported.stdout))
    read = {one.name: one.bytes_used for one in DwarfDebugReader().read_statics(built)}
    return declared, read


def test_a_plain_array_is_its_whole_length(sizes: tuple[dict[str, int], dict[str, int]]) -> None:
    declared, read = sizes

    assert read["g_bytes"] == declared["g_bytes"] == 2048


def test_an_array_of_structures_counts_every_element(
    sizes: tuple[dict[str, int], dict[str, int]],
) -> None:
    declared, read = sizes

    assert read["g_samples"] == declared["g_samples"]
    assert read["g_samples"] > 4096, "an element size would have been reported instead"


def test_both_dimensions_of_a_grid_are_counted(
    sizes: tuple[dict[str, int], dict[str, int]],
) -> None:
    declared, read = sizes

    assert read["g_grid"] == declared["g_grid"] == 8 * 16 * 2


def test_a_scalar_and_a_structure_are_their_own_size(
    sizes: tuple[dict[str, int], dict[str, int]],
) -> None:
    declared, read = sizes

    assert read["g_one"] == declared["g_one"]
    assert read["g_single"] == declared["g_single"]


def test_a_constant_table_is_sized_and_marked(
    sizes: tuple[dict[str, int], dict[str, int]],
) -> None:
    """On a target it costs flash, which is not the budget anyone means."""
    declared, read = sizes

    assert read["g_table"] == declared["g_table"] == 64 * 4


def test_the_read_only_table_is_told_apart_from_the_writable_ones(
    symbols: dict[str, bool],
) -> None:
    assert symbols["g_table"]
    assert not symbols["g_bytes"]
