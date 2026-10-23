"""A C file with a layout only the compiler can settle.

Padding, bit order and field widths are the compiler's decisions, so the
fixture reports its own offsets and the reader is checked against those
rather than against a layout a test assumed.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

FIXTURE = """
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

typedef struct {
    uint16_t numerator;
    int32_t offset_counts;
} calibration_t;

typedef struct {
    bool enabled;
    uint32_t sample_rate_hz;
    calibration_t calibration[2];
    double gain;
} channel_t;

typedef struct {
    channel_t channel[3];
    const char *name;
} config_t;

/* Nothing but pointers: a vtable has no value to watch. */
typedef struct {
    void (*open)(void);
    void *context;
    const char *name;
} vtable_t;

/* A pointer beside scalars: leaving it out must not take them with it. */
typedef struct {
    const char *label;
    uint32_t counter;
    void (*callback)(int);
    double level;
} mixed_t;

typedef struct {
    uint8_t enabled : 1;
    uint8_t mode : 3;
    int8_t trim : 4;
    uint16_t serial : 12;
} packed_t;

config_t g_config;
packed_t g_packed;
vtable_t g_vtable;
mixed_t g_mixed;
const uint32_t g_revision = 7u;
volatile int8_t g_temperature;
float g_unused_elsewhere;
static long double g_wide_one;
static uint64_t g_sequence;

unsigned long counter(void)
{
    static uint64_t g_calls;
    g_calls++;
    g_sequence++;
    return (unsigned long)g_calls;
}

int main(void)
{
    printf("%zu %zu %zu\\n",
        (size_t)((char *)&g_config.channel[1].calibration[0].offset_counts - (char *)&g_config),
        (size_t)((char *)&g_config.channel[2].gain - (char *)&g_config),
        (size_t)((char *)&g_config.name - (char *)&g_config));
    (void)counter();
    (void)g_revision; (void)g_temperature; (void)g_unused_elsewhere; (void)g_wide_one;
    (void)g_packed; (void)g_vtable; (void)g_mixed;
    return 0;
}
"""


def compiler_on_path() -> str | None:
    """Name of a compiler that is available, or None when there is none."""
    return shutil.which("gcc") or shutil.which("clang")


def build_fixture(directory: Path, compiler: str) -> tuple[Path, tuple[int, int, int]]:
    """Compile the fixture and ask it where its own members sit.

    Args:
        directory: Where to put the source and the executable.
        compiler: Compiler to invoke.

    Returns:
        The executable, and the three member offsets it reported.
    """
    source = directory / "fixture.c"
    source.write_text(FIXTURE, encoding="utf-8")
    executable = directory / ("fixture.exe" if sys.platform == "win32" else "fixture")

    compiled = subprocess.run(  # noqa: S603
        [compiler, "-g", "-O0", str(source), "-o", str(executable)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert compiled.returncode == 0, compiled.stderr
    reported = subprocess.run(  # noqa: S603
        [str(executable)], capture_output=True, text=True, check=True
    )
    first, second, third = (int(part) for part in reported.stdout.split())
    return executable, (first, second, third)
