# Bringing looper into a firmware project

This is the path from a firmware that builds for its target to the same
firmware running on your machine, answering a client. It is written for a
project that already exists and that you would rather not change.

The premise is that your firmware reaches hardware through one adapter
layer. That layer is what gets replaced; everything above it is compiled
unmodified. Nothing in your repository has to move, and the target build
does not learn that any of this happened.

## What you need, and where it comes from

Three projects, and it is worth knowing which does what, because only one
of them ends up in your build:

| Project | Is | You need it |
| --- | --- | --- |
| `looper-rt` | the C runtime compiled into the simulation | always |
| `looper-core` | `looper-cli`, which reads your headers and generates | to generate; not to build what it generated |
| `looper-gui` | the window that attaches to a running simulation | only to look at one |

`looper-rt` is C with no third party dependency. `looper-core` is the Python
tool. A build server that compiles committed generated sources needs only
the first.

## Keep it in one directory

Put everything the simulation adds under one directory of your repository --
`sil/` reads well -- and change nothing outside it:

```text
your-firmware/
├─ app/  bsp/  module/      your firmware, untouched
└─ sil/
   ├─ looper.toml           the build definition
   ├─ contract.toml         what the adapter functions mean
   ├─ Inc/                  headers standing in for the vendor library
   └─ src/                  the device model, the entry point, the stand-ins
```

Everything below is a file in that directory.

## 1. Read the adapter surface

Before building anything, find out what the adapter layer actually is:

```console
$ looper-cli analyze path/to/adapter/Inc -I path/to/other/Inc
9 modules, 50 functions, 2 exported data symbols
```

Two numbers matter. **Functions** is how much has to be simulated.
**Exported data symbols** is the one that surprises people: a vtable the
adapter defines is part of the surface, the generator cannot guess its
content, and step 4 is about what happens when you ignore it.

If this step cannot parse your headers, it is an include path short. Add it
to `parse_includes` rather than to `includes`: the two are separate because
reading a header needs a different set from compiling the firmware, and
conflating them makes both harder to get right.

## 2. Write the contract

The declaration says that `adapter_spi_transfer` takes a pointer and a
length. It does not say whether the adapter may keep that pointer, or which
argument is a bus number. The contract says, and the simulation is generated
from it.

```console
$ looper-cli analyze path/to/adapter/Inc --contract sil/contract.toml
```

Start with an empty contract and let the tool tell you what is missing; see
[Concepts](concepts.md#the-contract) for what can be said and
[Analysing a firmware](analysing.md) for reading the report. A parameter
with no contract is not an error, it is a gap the audit reports, and you can
work through them.

## 3. Write the build definition

`sil/looper.toml` says where everything is. The full key list is in
[Building a simulation](building.md#the-build-definition); these are the
ones you cannot avoid:

```toml
[simulation]
name = "my-simulation"

headers  = "../module/adapter/Inc"
contract = "contract.toml"

parse_includes = ["../module/contracts/Inc"]

sources  = ["src", "../app/Src", "../bsp/Src", "../module/general-com/Src"]
includes = ["Inc", "src", "../app/Inc", "../bsp/Inc"]

generated  = "build/generated"
executable = "build/my-simulation"
```

Paths are relative to the definition, so they stay short and the whole
thing moves with the directory.

## 4. The three things that always come up

The first build will not succeed, and it will fail in the same three ways
every project fails. None of them is a defect in your firmware.

### The vendor peripheral library

Your board support code calls the vendor's generated peripheral library --
Harmony, STM32Cube, whatever ships with the silicon. It is not on your
machine and it is not part of the adapter surface.

Declare the surface it uses in `sil/Inc/`, implement it in `sil/src/`, and
**make every function do nothing and return a zero value**. That sounds
careless and it is the point: the premise is that the firmware reaches
hardware through the adapter, so anything still calling the peripheral
library directly is bypassing that boundary. A stub that does nothing makes
the bypass visible in behaviour. A stub that answers plausibly hides it.

Two kinds of exception are worth making:

- **Route GPIO into the pin model**, so that pins the board support code
  drives directly are visible like every other pin. Carry the real pin
  numbers from the generated header, so a named pin in the inspector is the
  pin on the board.
- **Accept a configuration rather than refusing it**, where the firmware
  writes a setting and reads it back. Refusing is not the same claim as
  doing nothing: a controller that says no to its own bit timing is a broken
  controller, and firmware rightly refuses to start on one.

### Exported vtables dispatch to address zero

If `analyze` reported exported data symbols, this one is waiting for you.

The generator emits the symbol, because the firmware will not link without
it, but it cannot know what belongs inside, so it emits it zeroed behind an
escape hatch:

```c
#ifndef LOOPER_INIT_mcu_gpio_interface
#define LOOPER_INIT_mcu_gpio_interface {0}
#endif
const embd_gpio_interface_t mcu_gpio_interface = LOOPER_INIT_mcu_gpio_interface;
```

A zeroed table links cleanly and then dispatches to address zero on the
first call through it. That is a segmentation fault inside your firmware
with nothing in the trace to explain it, and it happens during start up,
before anything has run.

Fill it in the definition with the adapter entry points the generator *does*
emit, which is what the real adapter puts there on the target:

```toml
defines = [
    "LOOPER_INIT_mcu_gpio_interface={ .set = adapter_mcu_gpio_set, .get = adapter_mcu_gpio_get }",
]
```

### Units that cannot compile for a host

Some translation units have no host meaning: their body sits inside a
target-only `#if`, or they pin absolute addresses, or they assert about a
structure whose padding differs between compilers. Leave them out with
`exclude` and, where the firmware still needs what they did, put a host
version beside it in `sil/src/`.

See [Leaving a translation unit out](building.md#leaving-a-translation-unit-out)
for which of the three reasons applies and why it matters.

## 5. The entry point

The simulation supplies its own `main`, so the firmware's is excluded. Yours
brings the board up, starts the control channel and runs the firmware loop.
`looper::app` holds the part every simulation shares; see
{rt}`The runtime <runtime.html>` for what it does.

This is also where anything that has to happen *before* the firmware starts
goes -- provisioning a flash window, most commonly. See
[Modelling a flash that ships provisioned](buses.md#modelling-a-flash-that-ships-provisioned),
which is the difference between a derived channel carrying a value and
reading `no data` forever.

## 6. The device model

Now it builds and starts, and does nothing interesting, because nothing is
driving it. The device model is the code that answers as the hardware would:
a converter that produces samples, a port expander, a CAN peer.

Devices looper ships are a line in the definition:

```toml
components = ["as8510", "mcp23x08"]
```

Anything else you write, in C, attached to a bus. [Buses and
components](buses.md) is the whole of that subject, including when a model
can live in Python instead and when it cannot.

One piece is easy to miss: **a conversion nobody is told about is useless**.
On the board an interrupt says a sample is ready. If the routing lives in a
unit you had to exclude, keep the table and replace the handlers with a
function a device model calls when its source fires. An event with no
binding is an event the board has no source for, and it should not be
delivered.

## 7. Into your own build

`looper-cli build` does an incremental, parallel build and needs nothing
else. A project that already builds with CMake usually prefers the
simulation to be one more target, sharing one dependency graph and one
object cache:

```cmake
include(FetchContent)
FetchContent_Declare(looper_rt
    GIT_REPOSITORY https://example.invalid/looper-rt.git
    GIT_TAG        v0.1.0)
FetchContent_MakeAvailable(looper_rt)

looper_add_simulation(my-simulation
    DEFINITION ${CMAKE_CURRENT_LIST_DIR}/looper.toml
    GENERATED  ${CMAKE_CURRENT_BINARY_DIR}/generated)
```

Nothing is repeated there: the definition already says which directories the
firmware lives in and which are excluded, and the generator hands CMake all
of it. Both paths produce the same programme; see [Using CMake
instead](building.md#using-cmake-instead).

To keep the Python tool out of the build entirely, commit what
`looper-cli generate` wrote and configure with `-DLOOPER_GENERATE=OFF`.

## When start up crashes

It will, at least once, and the trace will be unhelpful because the crash is
inside firmware that was compiled without being asked about any of this.

Build with debug information -- `warnings = ["-Wall", "-g"]` -- and run it
under a debugger:

```console
$ gdb --args build/my-simulation --port 45771
```

A frame zero of `0x0000000000000000 in ?? ()` with real firmware frames
above it means a call through a null function pointer, which is the zeroed
vtable from step 4 almost every time.

Warnings are not errors here on purpose. The firmware sources are not yours
to change in this build, and a host compiler finds things the target
compiler does not.

## Where to go next

| Page | For |
| --- | --- |
| [Concepts](concepts.md) | what the adapter surface and the contract are |
| [Building a simulation](building.md) | every key of the definition |
| [Buses and components](buses.md) | writing the device model |
| [Firmware variables](variables.md) | reading and watching globals |
| [Analysing a firmware](analysing.md) | which question each tool answers |
| [Checking a simulation](checking.md) | timing, memory, expectations in pytest |
