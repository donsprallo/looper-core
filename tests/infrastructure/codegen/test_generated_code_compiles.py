"""End to end check that the generated simulation compiles, links and runs.

The generated code is C, so the only honest check is a C compiler. The test
parses a header, generates from it, builds the result together with a small
program that installs a hook, and runs it.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from looper.application.commands import GenerateSimulation
from looper.application.dto import GenerateSimulationRequest
from looper.infrastructure.codegen import CSimulationGenerator
from looper.infrastructure.contracts import TomlAdapterContractRepository
from looper.infrastructure.filesystem import FileSystemArtifactRepository
from looper.infrastructure.parsing import LibclangAdapterSurfaceRepository, ParseOptions

COMPILER = shutil.which("gcc") or shutil.which("clang")
requires_compiler = pytest.mark.skipif(COMPILER is None, reason="no C compiler on PATH")

ADAPTER_HEADER = """
#ifndef ADAPTER_DEMO_H
#define ADAPTER_DEMO_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef enum { DEMO_OK = 0, DEMO_BUSY = 1 } demo_result_t;

typedef struct {
    uint32_t id;
    uint8_t length;
} demo_frame_t;

demo_result_t adapter_demo_receive(demo_frame_t *frame);
bool adapter_demo_send(const uint8_t *data, size_t len, void (*done)(void *ctx, bool ok));
uint32_t adapter_demo_millis(void);
void adapter_demo_reset(void);

#endif
"""

CONTRACT = """
[adapter_demo_receive]
frame = { role = "output", written_at = "on_return" }

[adapter_demo_send]
data = { role = "input", lifetime = "borrowed" }
done = { role = "callback" }
"""

PROGRAM = """
#include <assert.h>
#include <string.h>

#include "looper_hooks.h"

static int calls = 0;

static demo_result_t fake_receive(demo_frame_t *frame)
{
    calls++;
    frame->id = 0x2A;
    frame->length = 8;
    return DEMO_BUSY;
}

int main(void)
{
    demo_frame_t frame;

    looper_hooks_reset();
    memset(&frame, 0xFF, sizeof frame);
    assert(adapter_demo_receive(&frame) == DEMO_OK);
    assert(frame.id == 0);
    assert(frame.length == 0);
    assert(adapter_demo_send(NULL, 0, NULL) == false);
    assert(adapter_demo_millis() == 0);

    looper_hooks()->adapter_demo_receive = fake_receive;
    assert(adapter_demo_receive(&frame) == DEMO_BUSY);
    assert(calls == 1);
    assert(frame.id == 0x2A);

    looper_hooks_reset();
    assert(adapter_demo_receive(&frame) == DEMO_OK);
    assert(calls == 1);
    return 0;
}
"""


def _generate(tmp_path: Path) -> Path:
    """Parse the fixture header and generate its simulation."""
    headers = tmp_path / "Inc"
    headers.mkdir()
    (headers / "adapter_demo.h").write_text(ADAPTER_HEADER, encoding="utf-8")
    contract = tmp_path / "contract.toml"
    contract.write_text(CONTRACT, encoding="utf-8")

    output = tmp_path / "generated"
    GenerateSimulation(
        surface_repository=LibclangAdapterSurfaceRepository(ParseOptions()),
        contract_repository=TomlAdapterContractRepository(),
        generator=CSimulationGenerator(),
        artifact_repository=FileSystemArtifactRepository(),
    ).execute(
        GenerateSimulationRequest(
            header_directory=headers, output_directory=output, contract_path=contract
        )
    )
    return output


@requires_compiler
def test_the_generated_simulation_compiles_links_and_honours_hooks(tmp_path: Path) -> None:
    assert COMPILER is not None
    output = _generate(tmp_path)
    (output / "main.c").write_text(PROGRAM, encoding="utf-8")
    executable = tmp_path / "simulation.exe"

    build = subprocess.run(  # noqa: S603
        [
            COMPILER,
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-o",
            str(executable),
            *(str(source) for source in sorted(output.glob("*.c"))),
            f"-I{output}",
            f"-I{tmp_path / 'Inc'}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert build.returncode == 0, build.stderr
    assert subprocess.run([str(executable)], check=False).returncode == 0  # noqa: S603
