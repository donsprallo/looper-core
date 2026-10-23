# User guide

## Installation

`looper` needs Python 3.13 or newer. The libclang front end ships as a wheel,
so no system LLVM installation is required.

```console
$ uv sync
$ uv run looper-cli --version
looper 0.1.0
```

To build and run the generated C code you also need a C compiler on `PATH`
(`gcc` or `clang`). The graphical inspector is an optional extra:

```console
$ uv sync --extra gui
```

### The two commands

| Command | Purpose |
| --- | --- |
| `looper-cli` | analyse an adapter, generate, build and run a simulation |
| `looper-gui` | attach to a running simulation and inspect it |

`looper` is kept as an alias of `looper-cli`. The two commands are separate on
purpose: `looper-cli` works on files and exits, while `looper-gui` attaches to
a process that is already running.

## Starting a simulation

**A simulation is your firmware, compiled for the host.** `looper` generates and
builds it; nothing in the tool runs it for you, because what runs is an
executable your project produces.

The quickest way to see the whole thing work is the example firmware in
`examples/blinky`: a small adapter, a firmware that blinks an LED, and a device
model that maps the adapter onto the runtime.

```console
$ uv run looper-cli run examples/blinky/looper.toml --port 45771
blinky listening on port 45771
```

Leave it running. In another terminal:

```console
$ uv run looper-gui --port 45771
```

`looper-cli run` generates the adapter, compiles it together with the runtime
and the firmware, and starts the result. `looper-cli build` stops after the
compile.

### For your own firmware

Write a `looper.toml` next to it and the same two commands apply:

```toml
[simulation]
name = "my-firmware"
headers = "../fw_in_adapter_pic32/Inc"
contract = "contract.toml"
sources = ["src", "bsp"]
includes = ["Inc", "src"]
parse_includes = ["../embd-contracts/Inc", "../fw_in_ioexpander/Inc"]
```

```console
$ uv run looper-cli run
```

See [Building a simulation](building.md) for every setting, and
{rt}`The runtime <runtime.html>` for the device model that maps your adapter
onto simulated hardware.

The window shows `LED_STATUS` toggling twice a second and an input pin
`BUTTON_MODE`. Toggle the button and the LED speeds up: the firmware read the
pin you drove.

Without the graphical extra, the same from Python:

```python
from looper.domain.model.simulation import SignalLevel
from looper.infrastructure.ipc import ProtobufSimulationSession

with ProtobufSimulationSession(port=45771) as session:
    for pin in session.read_gpio_pins():
        print(pin.identifier.display_name, pin.level.value, pin.is_active)
```

The sections below walk through doing the same for an adapter of your own.

## A first run

The walkthrough below uses `fw_in_adapter_pic32` and assumes its neighbouring
repositories sit next to it.

### 1. See what the adapter declares

```console
$ looper-cli analyze ../fw_in_adapter_pic32/Inc \
    -I ../embd-contracts/Inc \
    -I ../fw_in_ioexpander/Inc
```

```text
Adapter surface: ..\fw_in_adapter_pic32\Inc

  can          functions=7   records=3  enums=2
  flash        functions=7   records=0  enums=0
  gpio         functions=6   records=2  enums=1  data=mcu_gpio_interface, expander_gpio_interface
  i2c          functions=3   records=1  enums=1
  spi          functions=7   records=2  enums=2
  spi_dma      functions=8   records=1  enums=0
  timer        functions=6   records=0  enums=1
  uart         functions=5   records=2  enums=1
  utils        functions=1   records=0  enums=0

9 modules, 50 functions, 2 exported data symbols

57 declarations need a contract before generation:
  adapter_can_init.adapter  [parameter_not_contracted]
  ...
```

Each header becomes one module, named after the file with the `adapter_` prefix
removed. `data=` lists the `extern` symbols the simulation must define in
addition to the functions.

### 2. Write the contract

The list of gaps is the to-do list. Work through it one parameter at a time and
re-run `analyze` until it reports:

```text
Contract complete: every buffer and callback is specified.
```

Keep the finished contract beside the rest of the simulation, in
`sil/contract.toml`.

### 3. Generate the simulation

```console
$ looper-cli generate ../fw_in_adapter_pic32/Inc \
    -I ../embd-contracts/Inc \
    -I ../fw_in_ioexpander/Inc \
    --contract sil/contract.toml \
    -o build/sil
```

```text
Generated into: build\sil

  looper_hooks.h             405 lines  [c_header]
  looper_hooks.c              18 lines  [c_source]
  sil_adapter_can.c           92 lines  [c_source]
  ...

11 files, 50 functions simulated
```

### 4. Build and drive it

```console
$ gcc -std=c11 -Wall -Wextra -o test.exe \
    build/sil/*.c my_test.c \
    -Ibuild/sil -I../fw_in_adapter_pic32/Inc \
    -I../embd-contracts/Inc -I../fw_in_ioexpander/Inc
```

```c
#include <assert.h>
#include "looper_hooks.h"

static int sent = 0;

static adapter_can_result_t count_frames(
    adapter_can_t *adapter, uint8_t fifo_index, const adapter_can_frame_t *frame)
{
    (void)adapter; (void)fifo_index; (void)frame;
    sent++;
    return ADAPTER_CAN_RESULT_OK;
}

int main(void)
{
    looper_hooks_reset();
    looper_hooks()->adapter_can_send_frame = count_frames;

    run_one_firmware_cycle();

    assert(sent == 1);
    return 0;
}
```

## Commands

### `looper-cli analyze`

Reports what an adapter directory declares and what is still unspecified.

```console
looper-cli analyze HEADER_DIRECTORY [-I DIR]... [-D NAME[=VALUE]]... [--contract FILE]
```

| Option | Meaning |
| --- | --- |
| `-I`, `--include` | Additional include directory. Repeatable. |
| `-D`, `--define` | Preprocessor definition. Repeatable. |
| `--contract` | TOML contract to check the declarations against. |

Without `--contract` every pointer and callback is reported as uncontracted,
which is the quickest way to see the full list.

### `looper-gui`

Opens the inspector window against a running simulation.

```console
looper-gui [--host HOST] [--port PORT]
```

The same window opens from the subcommand `looper-cli gui`, with the same
options. Use whichever reads better in the context; `looper-gui` exists so that
a desktop shortcut or a task runner does not have to pass a subcommand.

| Option | Meaning |
| --- | --- |
| `--host` | Host the simulation listens on. Defaults to `127.0.0.1`. |
| `--port` | Port the simulation listens on. Defaults to `45771`. |

Needs the graphical extra (`uv sync --extra gui`) and a simulation started in
real time mode. See {gui}`The inspector <gui.html>`.

### `looper-cli build` and `looper-cli run`

Generate, compile, and start a simulation from a build definition. Documented
in full under [Building a simulation](building.md).

```console
looper-cli build [DEFINITION] [--allow-incomplete-contract]
looper-cli run   [DEFINITION] [--port PORT] [--virtual] [--no-build]
```

Both default to `looper.toml` in the working directory. `run` hands back the
exit code of the simulation.

### `looper-cli audit`

Inspects a project against its own contract without building or running it.
Documented in full under [Checking a simulation](checking.md).

```console
looper-cli audit [DEFINITION]
```

Defaults to `looper.toml` in the working directory. The command exits with
status 1 when it found something to act on, so it can stand in a pipeline
unattended.

### `looper-cli generate`

Writes the C simulation of an adapter directory.

```console
looper-cli generate HEADER_DIRECTORY -o OUTPUT [-I DIR]... [-D NAME[=VALUE]]...
                [--contract FILE] [--allow-incomplete-contract]
```

| Option | Meaning |
| --- | --- |
| `-o`, `--output` | Directory the generated sources are written to. Required. |
| `--contract` | TOML contract to generate from. |
| `--allow-incomplete-contract` | Generate although parameters lack a contract. |

Generation refuses to run while the contract is incomplete. The refusal names
the first ten gaps and exits with status 1. `--allow-incomplete-contract`
overrides this; uncontracted parameters then get the conservative default and
the report says how many.

Existing files in the output directory are overwritten. Generated files carry a
`Do not edit` banner — edit the contract or the generator, never the output.

## Include directories

Adapter headers include headers of neighbouring repositories, so pass `-I` for
each of them. Preprocessor definitions that select a variant go in with `-D`:

```console
$ looper-cli analyze Inc -I ../embd-contracts/Inc -D ADAPTER_SPI_PLIB=SPI1
```

The standard headers are a special case. Firmware headers are written for a
cross compiler, so the host's `<stdint.h>` is the wrong answer. `looper` appends
freestanding stand-ins for `<stdint.h>`, `<stdbool.h>`, `<stddef.h>` and
`<stdarg.h>` as the **last** include directory. Passing the real toolchain
include directory with `-I` takes precedence, because it is searched first.

The stand-ins declare the fixed width types as the C standard requires them. A
target whose `int` is not 32 bits wide needs its real toolchain headers.

## Troubleshooting

**`'xyz.h' file not found`** — a header of a neighbouring repository is missing
from the search path. Add it with `-I`. If the firmware project is built with
CMake, `CMAKE_EXPORT_COMPILE_COMMANDS` produces a `compile_commands.json` that
lists every include directory the real build uses.

**`N declarations have no contract`** — expected on a first run. Work through
the list, or pass `--allow-incomplete-contract` to see generated output first.

**`unknown_function` or `unknown_parameter` in the report** — the contract
names something the headers no longer declare. The adapter API changed; update
the contract entry.

**The generated code compiles but the firmware hangs** — an asynchronous
adapter is waiting for a completion callback that nothing invokes. Install a
hook that calls the callback. See [Known differences from
hardware](concepts.md#known-differences-from-hardware).

**`No simulation at 127.0.0.1:45771`** — the firmware is not running, exited, or
listens on another port. It prints the port it bound on start up.

**The inspector window does not tick** — the simulation runs on a virtual clock.
Start the firmware in real time mode. See {gui}`The inspector <gui.html>`.

**`undefined reference to looper_journal_record`** — generated sources were
compiled with `-DLOOPER_JOURNAL` but the runtime was not linked. Either link it
or set `record_calls = false` in the build definition.

**`No C compiler found`** — install `gcc` or `clang`, or name one in the build
definition with `compiler = "..."`.

**`No build definition at looper.toml`** — `build` and `run` look for
`looper.toml` in the working directory. Pass the path explicitly, or change
directory first.

## Using the Python API

Everything the command line does is available as use cases. Repositories are
abstract, so a different front end or output target only means a different
implementation:

```python
from pathlib import Path

from looper.application.dto import AnalyzeAdapterSurfaceRequest
from looper.application.queries import AnalyzeAdapterSurface
from looper.infrastructure.contracts import TomlAdapterContractRepository
from looper.infrastructure.parsing import LibclangAdapterSurfaceRepository, ParseOptions

options = ParseOptions(include_directories=(Path("../embd-contracts/Inc"),))
use_case = AnalyzeAdapterSurface(
    surface_repository=LibclangAdapterSurfaceRepository(options),
    contract_repository=TomlAdapterContractRepository(),
)

report = use_case.execute(
    AnalyzeAdapterSurfaceRequest(
        header_directory=Path("../fw_in_adapter_pic32/Inc"),
        contract_path=Path("sil/contract.toml"),
    )
)

print(report.function_count, report.is_contract_complete)
```
