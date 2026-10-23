# Building a simulation

A simulation is your firmware compiled for the host. `looper-cli build` does
the whole job: it generates the adapter, compiles it together with the runtime
and your own sources, and links one executable. `looper-cli run` builds and
then starts it.

```console
$ uv run looper-cli build examples/blinky/looper.toml

Built blinky

  executable  examples/blinky/build/blinky.exe
  compiler    gcc
  generated   3 files, 5 adapter functions simulated
```

```console
$ uv run looper-cli run examples/blinky/looper.toml --port 45771
blinky listening on port 45771
```

Both commands read a build definition. With no path given they look for
`looper.toml` in the working directory.

The blocks above show what lands on standard output. On a terminal you also
see each step as it happens, which is described under
[While it works](#while-it-works).

## The build definition

```toml
[simulation]
name = "blinky"

# The adapter headers the simulation is generated from.
headers = "Inc"
contract = "contract.toml"

# The firmware itself and the device model that maps the adapter onto the
# looper runtime.
sources = ["src"]
includes = ["Inc", "src"]

# Where generation and compilation put their output.
generated = "build/generated"
executable = "build/blinky"

record_calls = true
warnings = ["-Wall", "-Wextra", "-Werror"]
```

Every path is relative to the definition file, never to the working directory,
so the file can be checked in next to the firmware and used from anywhere.

| Key | Default | Meaning |
| --- | --- | --- |
| `name` | required | names the simulation and its default executable |
| `headers` | required | adapter header directory |
| `contract` | none | contract definition to generate from |
| `sources` | none | directories holding firmware and device model code |
| `includes` | none | include directories for the compiler |
| `exclude` | none | translation units to leave out of the build |
| `defines` | none | preprocessor definitions for the compiler |
| `generated` | `build/generated` | where generated sources are written |
| `executable` | `build/<name>` | what to link |
| `parse_includes` | none | include directories used only while reading headers |
| `parse_defines` | none | definitions used only while reading headers |
| `compiler` | detected | compiler to invoke |
| `standard` | `c11` | C standard |
| `warnings` | `-Wall -Wextra` | warning flags |
| `record_calls` | `true` | compile generated adapters with the call journal |
| `components` | none | devices looper ships that this board carries |
| `profile` | `false` | weave the firmware and the device model for profiling |
| `track_allocations` | `false` | put looper's wrappers in front of the allocator |
| `memory_budget` | `0` | writable static bytes the project allows itself, zero for no limit |

`profile` turns on the profiler described in
[Checking a simulation](checking.md#where-the-whole-simulation-spends-its-time).
It makes a different programme -- about forty nanoseconds per call, and
nothing woven gets inlined -- so it belongs in a build you are measuring
rather than in the one you leave switched on.

`track_allocations` and `memory_budget` belong to the memory analysis, also
described under [Checking a simulation](checking.md#where-the-memory-goes).
The first is a link time switch and changes no code; the second is checked
by `looper-cli audit`, which fails when the build does not fit.

`components` names the simulated devices from
[Buses and components](buses.md) that the board has, without their
`looper_` prefix:

```toml
components = ["as8510", "mcp23x08"]
```

They are opt-in rather than always compiled in, for a reason worth knowing:
a direct build compiles what it is given while a linker keeps only what a
library is asked for, so building them all would make the two paths
describe different programmes.

`parse_includes` exists because the two sets genuinely differ. Reading the
adapter headers may need a neighbouring repository that the simulation itself
never compiles, and a firmware project may define target macros that would be
wrong for the host build.

An `executable` without a suffix gets the one the platform needs, so
`build/blinky` becomes `build/blinky.exe` on Windows and every later check
looks at the file the linker actually wrote.

### Leaving a translation unit out

`sources` names directories, not files, because a firmware has too many
files to list and the list would rot. `exclude` is how a directory that is
otherwise right loses the one unit that is not:

```toml
sources = ["../app/Src", "../bsp/Src"]
exclude = [
    # The simulation brings its own entry point.
    "../app/Src/main.c",
    # Everything past the routing table is inside #if defined(__PIC32MZ).
    "../bsp/Src/platform_event_router.c",
]
```

Three reasons come up, and it is worth knowing which one applies:

- **The simulation supplies it instead.** `main.c` is the usual one: the
  simulation's entry point starts the control channel and then runs the
  firmware loop.
- **It is target-only.** A unit whose body is inside `#if defined(__PIC32MZ)`
  or similar holds nothing a host build can use. Defining the macro to get
  it compiling drags in the vendor peripheral library behind it, which is a
  far larger stand-in than replacing the one unit.
- **It cannot compile for a host at all.** A layout that pins absolute byte
  addresses, or static assertions about a structure whose padding differs
  between the target compiler and a host one, will fail before anything else
  can go wrong. Excluding it is honest about the limit; pretending otherwise
  produces a simulation that disagrees with the board.

A unit named here is left out of the build, not stubbed. If the firmware
calls into it, the link fails and says which symbol is missing, which is the
answer you want: either something has to stand in for it, or the exclusion
was wrong.

## What gets compiled

Three groups of sources:

1. the generated adapter in `generated`
2. the looper runtime, which ships inside the package
3. every `*.c` under each directory in `sources`

Each is compiled on its own into `build/objects`, as many at a time as the
machine has cores, and the objects are then linked. Include directories are
`generated`, `headers`, everything in `includes`, and the runtime headers.
Nothing else is implied. A unit the compiler rejects stops the build before
the link, and what it said is printed under the name of the compiler that
said it.

### What it builds again, and what it keeps

A unit is compiled again when any of these is true, and kept otherwise:

- there is no object file for it
- the source, or **any header it includes**, is as new as the object
- the command has changed -- a flag, a `-D`, a different compiler path
- the last attempt failed

The headers come from the compiler itself: each unit is compiled with
`-MMD`, which leaves beside the object the list of everything that went
into it. That is the only honest answer to the question, because nothing
else knows which header a unit pulls in four levels down. The command is
kept beside the object too, in a readable `.cmd` file, and only after the
compiler agreed -- a command remembered after a failure would describe an
object that was never written.

Linking is skipped on the same terms: if no unit was compiled and the
executable is newer than every object, there is nothing to produce. The
link command lists every object, so a source added or deleted changes it
and the link happens anyway.

Everything unknown counts as out of date. Getting this wrong in the
cheap direction costs a second; getting it wrong in the other direction
produces an executable that runs, answers, and is not the code being
worked on. `--rebuild` compiles the lot regardless, and deleting
`build/objects` has the same effect.

Generation plays along: a generated file whose content has not changed is
left on disk untouched, timestamp and all. Writing it out regardless would
give the hooks header a new date before every build, and most of the
simulation includes it.

## Commands

### `looper-cli build`

```console
looper-cli build [DEFINITION] [--allow-incomplete-contract] [--rebuild] [-q]
```

Generates and compiles. The generated sources are an intermediate product; the
build does not stop between the two steps, because a directory of generated
code that nobody should edit is not a useful place to pause.

A compiler error is reported with the compiler name and its full output, and
exits with status 1.

### `looper-cli run`

```console
looper-cli run [DEFINITION] [--port PORT] [--virtual] [--no-build]
               [--allow-incomplete-contract] [--rebuild] [-q]
```

Builds, then starts the simulation in the foreground. It inherits the terminal,
so its output appears as it is produced and Ctrl+C reaches it directly.

`--port` and `--virtual` are passed to the simulation. `--no-build` starts the
existing executable unchanged and fails if there is none.

**The exit code is the exit code of the simulation**, so a run that ends badly
is visible to a script or a CI job. Stopping a simulation with Ctrl+C counts as
a clean stop, because that is the normal way to end one.

Building first is the default because a stale executable is the most expensive
kind of confusion: it runs, it answers, and it is not the code being worked on.

## While it works

Every command that reads headers or starts a compiler says what it is doing,
one line per step, on **standard error**:

```console
$ looper-cli build sil/looper.toml
build  sil/looper.toml

  ✔ Reading the build definition      0.00 s  measuring-unit
  ✔ Reading the adapter headers       1.21 s  50 functions
  ✔ Reading the contract              0.01 s  50 functions, 12 roles
  ✔ Generating the simulation         0.14 s  11 files
  ✔ Writing the sources               0.02 s  sil/build/generated
  ⠙ ███████████░ 6/6  Compiling and linking  94/143 app_config.c  5.6 s
```

The live line carries a spinner, a bar and how long the step has been
running, so that a compile that takes half a minute is visibly working
rather than possibly hung. When the step finishes the same line is replaced
by what it came to.

The compiler is the step worth watching, so it is the one step that reports
its own parts: one translation unit at a time, named as it finishes, and the
bar creeping through that step rather than standing still at it. The units
are compiled in parallel, so the names arrive out of order -- what the
counter says is how many are done, not which.

Three things are worth knowing:

- **The report goes to standard output, the progress to standard error.**
  `looper-cli build > report.txt` keeps the report clean and leaves the
  display on the terminal.
- **It adapts to where it is writing.** Redirected or piped, there is no
  spinner, no colour and no rewriting -- one plain line per finished step,
  which is what a CI log wants. A console that cannot encode the drawing
  characters gets `+` and `#` instead, because a progress display that
  breaks the build it reports on is worse than none.
  [`NO_COLOR`](https://no-color.org) turns the colour off.
- **A step that fails stays open and is marked.** The step that raised is
  closed with a red mark and the word `failed`, and the error follows it.

Every command takes `-q` / `--quiet` to work without any of it. `run`
suppresses it by itself when `--no-build` leaves nothing to report.

## Using CMake instead

`looper-cli build` does its own incremental, parallel build, which for a
firmware of 143 units measures like this on fourteen cores:

| | |
| --- | --- |
| everything, one compiler invocation (how it used to be) | 34 s |
| everything, one invocation per unit | 9 s |
| after touching a device model header (7 units) | 0.7 s |
| after touching a runtime header (51 units) | 3.7 s |
| nothing changed | 0.4 s |

A project that already builds with CMake may still prefer to declare the
simulation as one more target, so that the simulation and the rest of its
build share one dependency graph, one object cache and one set of
conventions rather than sitting beside each other.

```cmake
include(FetchContent)
FetchContent_Declare(looper_rt
    GIT_REPOSITORY https://example.invalid/looper-rt.git
    GIT_TAG        v0.1.0)
FetchContent_MakeAvailable(looper_rt)

looper_add_simulation(my-simulation
    DEFINITION ${CMAKE_CURRENT_LIST_DIR}/looper.toml
    GENERATED  ${CMAKE_CURRENT_LIST_DIR}/build/generated)
```

Those nine lines are the whole of it, even for a firmware of ninety
translation units across eighteen directories. The definition already says
which they are, which are excluded and which include directories they need,
so nothing is repeated here.

A project whose own CMake already knows its firmware sources hands them over
instead:

```cmake
looper_add_simulation(my-simulation
    DEFINITION ${CMAKE_CURRENT_LIST_DIR}/looper.toml
    GENERATED  ${CMAKE_CURRENT_LIST_DIR}/build/generated
    SOURCES    src/main.c src/device_model.c ${FIRMWARE_SOURCES})
```

`examples/blinky/CMakeLists.txt` is that one. Either way the compile flags,
the preprocessor definitions and the C standard come from the definition, so
the two build paths cannot quietly differ.

Two library targets come with it:

| Target | What it is |
| --- | --- |
| `looper::runtime` | the clock, the models, the protocol and the server |
| `looper::components` | the simulated devices looper ships |
| `looper::app` | the entry point every simulation shares |

`looper_add_simulation` links both. A project that wants to write its own
loop links `looper::runtime` alone and calls `looper_server_poll` itself.

### The generation step

Generation runs while CMake configures, not while it builds, because what it
produces is part of what has to be configured: a header added to the adapter
is a source file added to the target, and CMake has to know that before it
writes a build graph. It writes `looper_generated.cmake` describing the
build, and CMake reads that rather than globbing or guessing:

| Variable | What it holds |
| --- | --- |
| `LOOPER_GENERATED_SOURCES` | what the generator wrote |
| `LOOPER_PROJECT_SOURCES` | the firmware and device model, exclusions applied |
| `LOOPER_INCLUDE_DIRECTORIES` | every header directory the firmware needs |
| `LOOPER_COMPILE_DEFINITIONS` | the definitions, `LOOPER_JOURNAL` included |
| `LOOPER_COMPILE_OPTIONS` | the flags, `-g` among them |
| `LOOPER_C_STANDARD` | the standard the definition asks for |

The definition is read by both, so the header directory and the output are
written down once:

```console
$ looper-cli generate --definition looper.toml
```

### Building without the tool

The generation step is the only part that needs Python. A project that would
rather not have it in the build commits what `looper-cli generate` writes and
configures with:

```console
$ cmake -S . -B build -DLOOPER_GENERATE=OFF
```

The generated sources follow from the headers and the contract, so a
committed copy is a copy rather than a fork. Someone has to remember to
regenerate when an adapter header changes; configuring with the default back
on is what does that.

Point `-DLOOPER_CLI` at the tool when it is not on `PATH`, for example
`-DLOOPER_CLI="uv run looper-cli"`.

### The two paths produce the same programme

They compile the runtime differently: `looper-cli build` puts it in the
executable, CMake links it as a library. The library is built with debug
information whatever the build type, so both describe the same thing down
to the last variable -- 23 671 of them for one real firmware, the same set
either way.
A test asserts it, because a library quietly built without debug
information would still produce a working simulation and a variable listing
missing looper's own state, which is the kind of difference nobody notices
until they go looking for something.

See {rt}`The runtime <runtime.html>` for the direct compiler invocation.
