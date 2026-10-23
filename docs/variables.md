# Firmware variables

A pin is high or low and a channel is a measurement. A variable is neither:
it is whatever the firmware keeps in memory, and most of what a firmware
knows about itself is in there rather than on any wire.

The inspector can list those variables, watch them while the firmware runs,
plot them beside the analog channels, and write them.

```console
$ uv run looper-cli run examples/blinky/looper.toml   # terminal one
$ uv run looper-gui --port 45771                      # terminal two
```

The Variables page lists what the build describes, arranged the way the
firmware declares it. A structure opens into its members and an array into
its elements:

```text
+------------------------------------------------------+------------------+
| Variable                      | Type       | Address  | Watched          |
|-------------------------------|------------|----------|------------------|
| v g_config                    | 5 values   |          | filtered_current |
|   v channel                   | 4 values   |          |          1000.0  |
|     v [0]                     | 2 values   |          | status.led_on    |
|         gain                  | float 8 B  | 0x1400.. |               1  |
|         enabled               | bool 1 B   | 0x1400.. |                  |
|     > [1]                     | 2 values   |          |  [ Remove ]      |
|   filtered_current            | float 8 B  | 0x1400.. |                  |
|------------------------------------------------------|  [ 42 ] [Write]  |
| 7 of 23593 variables                     [ Watch ]   |                  |
+------------------------------------------------------+------------------+
```

Double clicking a branch opens it; double clicking a value watches it.

The search field takes several words and requires each of them to appear
somewhere in the path, in any order, so `chan gain` finds
`channel[0].calibration.gain` without anyone having to remember what sits
between the two. A search narrows the tree to the matching values and the
steps that lead to them, and opens it so the matches are in view. Past two
hundred matches it stays closed, because opening it would take longer than
the search did.

## The build has to carry debug information

The variables come out of the executable, so it has to have been built with
`-g`:

```toml
warnings = ["-Wall", "-Wextra", "-Werror", "-g"]
```

Without it the page says so and stays empty. Nothing else changes: a build
without debug information runs exactly as before.

## Only the firmware is listed

Three programmes end up in one executable, and all three have variables:

| Whose | What | One firmware |
| --- | --- | --- |
| the firmware | what you came to see | 14 287 |
| the simulation | ring buffers, sockets, the pin and channel models | 8 402 |
| the toolchain | whatever the C runtime needs to start a process | 91 |

Two of them are apparatus, and showing apparatus beside a measurement
buries the answer. They are left out, and the **internals** tick box brings
them back. The status line says how many are being held back, so nobody
hunts for one that is simply hidden.

They are recognised differently, because what is knowable about them
differs:

- **The simulation's** units are named by the package itself, and matched by
  file name rather than by path. The same runtime is compiled from one
  place by `looper-cli` and from another by a CMake project that fetched
  it, and a path would recognise only one of them.
- **The toolchain's** units say where they were compiled, and it was not
  here. Everything this build compiled was compiled in the directory the
  executable landed in, below it, or above it, depending on who did the
  building; a unit from a prebuilt library carries a build tree from
  another machine and another year.

The second is a judgement rather than a fact, so it is made in the
direction that can be undone: being wrong only hides something the tick box
brings back.

## What is listed

Every scalar inside a **global** variable. Structures and arrays are walked
into, so what you pick is a number rather than an aggregate:

```text
g_app_config.active.measurement.channel[0].calibration[1].offset_counts
```

Bit fields are included. A packed flag is given the byte its first bit falls
in, together with the position and width of the run of bits it occupies:

```text
status.led_on          unsigned 1 bit    0x1400428d8
status.blinking_fast   unsigned 1 bit    0x1400428d8
status.toggle_count    unsigned 5 bits   0x1400428d8
```

Three fields, one address. Only the bit range tells them apart, and writing
one leaves the bits beside it exactly as they were.

Four things are deliberately absent:

- **Locals.** A local lives on a stack frame that exists while its function
  runs, so it has no address a watch could keep reading.
- **Statics inside functions.** They do have an address, but they are not
  globals and they are not named like one: two functions may each declare a
  `counter`.
- **Pointers.** A pointer's value is an address: it says where the firmware
  put something, not what the firmware is doing, and plotted it is noise.
  Showing what it points at instead is a different question and a much
  harder one -- a `void *` has no target type to show, a function pointer
  has nothing to read, and any pointer may be stale -- so neither is offered
  rather than one of them badly.
- **Types a `double` cannot hold**, such as a `long double`.

A variable made of nothing but pointers therefore does not appear at all.
That is most of what it removes: in one firmware, leaving pointers out drops 891
values and makes 73 variables vanish, and every one of them is a vtable, a
generated descriptor table or a C runtime internal. The scalars beside a
pointer are unaffected.

A deeply nested structure is walked eight levels deep and an array expands to
its first thirty two elements. Beyond that a listing stops being something a
person can use.

### Two files, one name

A variable declared `static` is private to its translation unit, so two
units may each have a `g_initialized` and mean different memory. One
firmware has three. They are listed separately, and only then is the declaring file put
beside the name:

```text
g_initialized (app_flash.c)
g_initialized (product_signal.c)
g_initialized (bsp_timebase.c)
```

A name only one file declares is left alone, which is nearly all of them.
Searching still works on the name the firmware uses, so `g_initialized`
finds all three.

## Watching

A watch is read **once per firmware loop iteration**, inside the simulation.
A client polling over the control channel could only see whatever happened to
fall on a poll; this way a watch has the resolution of the firmware.

Only changes are recorded. A sample on an analog channel means the firmware
looked at it, which is worth knowing even when the value repeats. A watch is
read because the simulation polls, so recording an unchanged value would
record the polling rather than the firmware.

Watched variables share the trace with the analog channels and appear in the
Scope legend next to them. Up to 64 can be watched at once.

## Writing

A writable variable can be given a value, which lands in the firmware's own
memory and is acted on from the next loop iteration.

Three writes are refused:

- a variable the firmware declared `const`, which on a target could be in
  flash;
- a value outside the range the variable can hold, named in full
  (`9999999999 is outside the range 0 to 4294967295`), which for a bit field
  is the range its own bits can hold: five bits stop at 31;
- anything at all, once the watch has been removed.

An integer is truncated towards zero, which is what the C assignment this
stands in for would do. A bit field is written by reading its bytes,
replacing its own bits and putting the rest back, so a flag beside it keeps
whatever it had.

## Addresses, and why there are two of them

Debug information names the addresses the linker chose. Windows and Linux
both relocate an image when they load it, so the address in the running
process is somewhere else, and every address shifts by the same distance.

The two halves come from the only two places that can answer honestly:

| Half | Source |
| --- | --- |
| the base the executable was linked against | the executable file |
| the base the process was loaded at | the simulation, in its greeting |

The process cannot report the first. A relocating loader overwrites the
header field that held it, so a process asking itself gets its own runtime
base back and would report a shift of zero. The executable file still has the
right answer, and a client reads that file anyway to get at the debug
information -- which is also what stops the two halves describing different
builds.

An address that lands outside the running image is refused rather than read.
A stale build would otherwise take the firmware down, which is a confusing
way to find out that the executable moved on.

## Where this is not a debugger

A debugger stops the firmware. This does not: everything here happens between
two loop iterations of a firmware that keeps running. That is the point, and
also the limit. There are no breakpoints, no call stacks, and no locals,
because all three need a stopped program to mean anything.
