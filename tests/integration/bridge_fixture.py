"""A simulation that exists only to have its buses bridged.

Nothing here is firmware. It registers a UART and a CAN bus, puts the
shipped bridges on them, and on every pass writes one byte and sends one
frame, so that a test on the other end of a socket has something to
catch and somewhere to throw something back.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from looper.infrastructure.build.project_sources import runtime_units
from looper.infrastructure.runtime_location import (
    component_sources,
    runtime_include_directories,
)

UART_BUS = 0
CAN_BUS = 1
UART_PORT = 0
CAN_BASE_ID = 0x700
OUTBOUND_BYTE = 0xA5
OUTBOUND_ID = 0x321

FIXTURE = """
/* A simulation whose whole purpose is to have its buses bridged. */
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>

#include "looper_app.h"
#include "looper_bus.h"
#include "looper_clock.h"
#include "looper_can.h"
#include "looper_tcp.h"
#include "looper_udp.h"
#include "looper_uart.h"

#define UART_BUS 0u
#define CAN_BUS 1u
#define UART_PORT 0u
#define CAN_BASE_ID 0x700u
#define OUTBOUND_BYTE 0xA5u
#define OUTBOUND_ID 0x321u
#define IDLE_MICROSECONDS 200u
#define OUTBOUND_EVERY_MICROSECONDS 20000u

/* Ports come from the command line so that two tests never collide. */
static uint16_t tcp_uart_port;
static uint16_t tcp_can_port;
static uint16_t udp_uart_port;
static uint8_t inbound[64];
static uint64_t emitted_at;

static void prepare(void)
{
    looper_bus_register(UART_BUS, LOOPER_BUS_KIND_UART, "UART1");
    looper_bus_register(CAN_BUS, LOOPER_BUS_KIND_CAN, "CAN1");
    (void)looper_tcp_uart(UART_BUS, UART_PORT, "Console", tcp_uart_port);
    (void)looper_tcp_can(CAN_BUS, CAN_BASE_ID, "Gateway", tcp_can_port);
    (void)looper_udp_uart(UART_BUS, UART_PORT + 1u, "Telemetry", udp_uart_port, NULL, 0u);
}

static bool start(void)
{
    return true;
}

/*
 * One byte on each bridged port and one frame per pass, so the far side
 * always has something arriving and a test never has to make the
 * firmware do anything.
 *
 * Taking what was injected is the other half, and it is what a real CAN
 * controller's model would do. Until something takes a frame off the
 * queue it has not reached the firmware, and the recording says so.
 */
static void step(void)
{
    const uint8_t byte = (uint8_t)OUTBOUND_BYTE;
    looper_can_frame_t frame = {.id = OUTBOUND_ID, .extended = false, .length = 2u};

    frame.payload[0] = 0x11u;
    frame.payload[1] = 0x22u;
    /* On a cadence rather than every pass: the recording holds a bounded
     * number of exchanges, and a bus chattering at the speed of the loop
     * would push what a test is looking for out of it before the test
     * could read it. */
    const uint64_t now = looper_clock_microseconds();

    if (now - emitted_at >= OUTBOUND_EVERY_MICROSECONDS) {
        emitted_at = now;
        (void)looper_uart_write(UART_BUS, UART_PORT, &byte, 1u);
        (void)looper_uart_write(UART_BUS, UART_PORT + 1u, &byte, 1u);
        (void)looper_can_send(CAN_BUS, &frame);
    }
    looper_component_run();
    while (looper_can_take(CAN_BUS, NULL)) {
        /* Taken, which is what records it as having reached us. */
    }
    (void)looper_uart_read(UART_BUS, UART_PORT, inbound, sizeof(inbound));
    (void)looper_uart_read(UART_BUS, UART_PORT + 1u, inbound, sizeof(inbound));
}

int main(int argc, char **argv)
{
    static const looper_application_t bridged = {
        .name = "bridged",
        .prepare = prepare,
        .start = start,
        .step = step,
        .idle_microseconds = IDLE_MICROSECONDS,
    };

    /* The three bridge ports, then whatever looper_main understands. */
    if (argc < 4) {
        return 2;
    }
    tcp_uart_port = (uint16_t)atoi(argv[1]);
    tcp_can_port = (uint16_t)atoi(argv[2]);
    udp_uart_port = (uint16_t)atoi(argv[3]);
    return looper_main(argc - 3, &argv[3], &bridged);
}
"""


def compiler_on_path() -> str | None:
    """Name of a compiler that is available, or None when there is none."""
    return shutil.which("gcc") or shutil.which("clang")


def build_bridged_simulation(directory: Path, compiler: str) -> Path:
    """Compile the bridged simulation against the runtime and components.

    Args:
        directory: Where to put the source and the executable.
        compiler: Compiler to invoke.

    Returns:
        The executable.
    """
    source = directory / "bridged.c"
    source.write_text(FIXTURE, encoding="utf-8")
    executable = directory / ("bridged.exe" if sys.platform == "win32" else "bridged")
    command = [
        compiler,
        "-std=c11",
        "-g",
        "-O1",
        str(source),
        *(str(one) for one in runtime_units()),
        *(str(one) for one in component_sources(("tcp", "udp"))),
        "-o",
        str(executable),
        *(f"-I{one}" for one in runtime_include_directories()),
    ]
    command.append("-lws2_32" if sys.platform == "win32" else "-lm")
    compiled = subprocess.run(command, capture_output=True, text=True, check=False)  # noqa: S603
    assert compiled.returncode == 0, compiled.stderr or compiled.stdout
    return executable
