# Analysing a firmware

[Checking a simulation](checking.md) describes each tool and how it works.
This page is the other way round: it starts from a question you actually
have, says which tool answers it, and — the part that matters — says what
the answer does and does not mean.

| Your question | Where to look |
| --- | --- |
| Is any of this real, or is the simulation pretending? | [Is it honest?](#is-it-honest) |
| Why is this value empty / stuck at zero? | [Why is nothing there?](#why-is-nothing-there) |
| What is slow? | [Where does the time go?](#where-does-the-time-go) |
| Will it fit on the target? | [Will it fit?](#will-it-fit) |
| Did my change break something? | [Did it change?](#did-it-change) |
| What is on the wire? | [What crossed the bus?](#what-crossed-the-bus) |

The one rule that runs through all of it: **a simulation runs your firmware
on a computer that is nothing like your board.** Some numbers are the
firmware's own and mean the same there; some belong to this machine. Every
section below says which is which, and the tools say so too.

## Is it honest?

Before any measurement is worth reading, the simulation has to be doing
something real. The failure that matters is quiet: an adapter function
nothing implements returns zero, and the firmware believes it.

**Start here, before you build:**

```console
$ uv run looper-cli audit
```

Read it in this order:

1. **`bus_function_without_role`** — the firmware calls it, nothing
   implements it, and it is returning the zero value. This is the one that
   makes a firmware "behave strangely for no reason".
2. **`borrowed_pointer_to_local`** — a real fault on the target, usually
   invisible until the timing changes.
3. **`exported_data_without_initialiser`** — a table of function pointers
   left at zero. The first call through it crashes.
4. **"declared functions no source names"** — not a fault. It tells you
   which parts of the adapter this board does not use.

**Then, while it runs, open the Timing tab** and look at the two call
columns:

```text
adapter_spi_dma_is_busy    7926 calls, 0 answered
```

Seven thousand times a second the firmware asked "are you busy?" and was
told "no" by a function nobody wrote. That is not a measurement of your
firmware; it is a hole in the model.

> **The conclusion to draw:** every unanswered call is a piece of the board
> that is not being simulated. Decide for each one whether it matters. A
> `gpio_toggle` nobody answers is usually fine; a `spi_transfer` nobody
> answers means the driver above it is being lied to.

## Why is nothing there?

A channel that reads `0` and a channel nothing has ever written look the
same on a screen, and they mean entirely different things. looper
distinguishes them: a channel the firmware registered but never published
reads **`no data`**.

```text
  2 POWER            output  400.6 W
  6 P1A_DISCHARGE    output  0 Ah
  7 P1B_BALANCE      output  no data
```

`P1A_DISCHARGE` is publishing and happens to be zero — nothing has been
drawn yet. `P1B_BALANCE` has never published anything: a charge balance on
a voltage probe is not a quantity, and the firmware does not compute one.

**What that means:** the channel is registered and wired correctly — the
firmware simply never produces the value. In almost every case the cause is
the firmware's own configuration, read **once at start up**. One measuring
firmware is the example: its product defaults set

```c
.power = APP_VALUE_SOURCE_DISABLED,
.work  = APP_VALUE_SOURCE_DISABLED,
```

and the consumers that would compute power are built from that
configuration while the firmware starts. So:

- Writing the configuration byte from the Variables tab afterwards does
  **not** help. The consumer was already built disabled; the byte is read
  once and never again.
- What does help is giving the firmware the configuration it expects
  **before** it starts. A board that left a factory has been provisioned:
  somebody wrote a configuration into its NVM. A fresh simulation has not,
  which is why a derived channel can read `no data`. A device model can do
  what the factory does — once, and only into a flash window that is still
  empty — after which the derived channels appear. See [Modelling a flash
  that ships provisioned](buses.md#modelling-a-flash-that-ships-provisioned)
  for how, and for how to get an unprovisioned board back.
- The other two routes are the firmware's own configuration transport, or a
  device model that answers with different defaults.

Note what provisioning does *not* do: `P1B_BALANCE` above is still empty.
Switching a calculation on does not make the firmware invent one it has no
input for.

> **The conclusion to draw:** `no data` is a statement about the firmware's
> configuration, not about looper. Before hunting for a wiring fault, check
> whether the firmware was ever asked to compute the thing.

If a channel shows `no data` and you believe it *should* be publishing, the
Timing tab is the next stop: if the function that would publish it never
runs, it appears there with no calls at all.

## Where does the time go?

Two pages, two questions, and they are easy to confuse.

**Timing — what does one call cost?** A flat ranking, one row per function,
with calls, mean and worst. Use it when you want to know whether something
is slow *per call*, or how often it happens.

**Profile — where did the second go?** A tree grouped by origin and
directory, with shares that add up. Use it when you want to know what is
eating the loop.

The difference is self time against total time:

```text
app_run                 7.5 s total,   107 ms self
application_signal_...  2.3 s total,    60 ms self
```

`app_run` is not slow. It *contains* everything. The 107 ms is what it spent
in itself. Only self times add up, which is why the profile's percentages
mean something and a column of totals does not.

> **The conclusion to draw:** a large total with a small self time is a
> conductor — look at its children. A large self time is a worker, or a
> function calling something that is not instrumented (a library routine
> has nowhere else to put its time).

**And the warning that matters:** these are host times. A simulated
converter answering over a function call has nothing in common with a real
one over SPI at 4 MHz. What transfers is the *shape*: which model is
expensive, which call happens far more often than you thought, and whether
something got slower since yesterday.

## Will it fit?

The Memory tab, and `looper-cli audit` for the part that needs no run.

**Static — read it first.** It needs no simulation at all and it is the
number closest to a target's RAM:

```text
Static memory: 73.0 KiB of writable static memory in the firmware
               (3371.0 KiB including looper's own, 2527 objects)
    largest objects:
         2.0 MiB  samples            looper_trace.c
        28.4 KiB  g_signal_service   product_signal.c
```

Read-only objects are counted apart: on a target they cost flash. The
firmware's own figure leads, and it is the one to read: looper's own
recording rings are megabytes and are not on your board.

Set a budget and let a pipeline watch it:

```toml
memory_budget = 65536
```

**Stack — the depth is the part that transfers.**

```text
deepest 2.0 KiB over 22 frames
    step → app_run → application_runtime_run → ... → signal_of
```

Twenty two nested frames is twenty two on the board as well; the 2.0 KiB is
this machine's. The exception, and it is the useful one: a function that
declares `uint8_t buffer[2048]` puts 2048 bytes on the stack everywhere.
The "largest frames" list is where you find those.

**Heap — the question is usually binary.**

```text
nothing was allocated
```

For firmware that forbids dynamic memory after start up, that is the whole
answer, and it is now a measurement rather than a code review. If something
does allocate, the sites are named and the C runtime's own allocations are
reported apart from the firmware's — otherwise every program looks like it
leaks.

> **The conclusion to draw:** use the structure, not the bytes. "Twenty two
> frames deep and one function holds a 2 KiB buffer" is a finding. "2.0 KiB
> of stack" is not a target figure.

## Did it change?

Everything above is also available to `pytest`, which is where it becomes
useful day to day — not as a number you look at, but as a number that fails
a build.

```python
from looper.testing import Expectations


def test_the_measurement_path_still_works(session):
    check = Expectations(session)
    check.channel(0, "P1A").reaches(1.0, tolerance=0.01, within_seconds=0.2)
    check.call("adapter_spi_dma_transfer").happened_at(8000)
    check.memory().never_allocates()
    check.stack().no_deeper_than(32)
    check.bus(2, "CAN2").nothing_refused()

    report = check.evaluate(for_seconds=1.0)
    assert report, report.summary
```

A failure says what was expected and what was seen:

```text
2 of 5 met
FAIL P1A     expected 1 +/- 0.01 within 0.2 s   saw never closer than 0.41
FAIL CAN2    expected nothing refused           saw 3 of 1586 refused at 0x701
```

Pick thresholds that catch a regression rather than ones that describe
today: `no_deeper_than(32)` when the firmware is at 22 is a useful guard,
`no_deeper_than(22)` is a tripwire that fires on the next refactor.

`looper-cli audit` exits non-zero when it finds something to act on, so the
static half fits a pipeline without a test at all.

## What crossed the bus?

The Buses tab records every exchange with its payload, and marks the ones
nothing took. The question it answers best is "the firmware says it sent
it — did it?".

Two things to know when reading it:

- An exchange marked **refused** crossed a bus with nothing attached at that
  address. On a real board that is a wire going nowhere.
- The recording is bounded. A chatty bus overflows it between two polls, and
  what you are shown is the newest, with the rest counted. Expectations
  report the loss rather than quietly measuring the ring.

To reach something outside the process — a terminal on a UART, a tool
watching CAN — attach a bridge; see [Buses and
components](buses.md#taking-a-bus-out-of-the-process).

## A worked example

A measuring firmware of some 140 translation units, from nothing to a
conclusion:

```console
$ looper-cli audit path/to/looper.toml
bus_function_without_role:
  adapter_spi_transfer
    the firmware uses it, the contract gives it no role and no device model
    hooks it, so it returns the zero value and nothing reaches the bus

Static memory: 73.0 KiB of writable static memory in the firmware
1 defect to act on
```

Already two facts without running anything: the asynchronous SPI path is not
modelled, and the firmware itself holds 73 KiB of writable static memory.

```console
$ looper-cli run path/to/looper.toml --port 45771
$ looper-gui --port 45771 --project path/to/looper.toml
```

- **Signals**: `P1A`, `P1B`, `POWER`, `WORK` and the `P1A` balances carry
  values, because the device model provisions the flash the way a factory
  would. The `P1B` balances say `no data`: a charge balance on a voltage
  probe is not a quantity the firmware computes.
- **Timing**: `adapter_spi_dma_transfer` 7926 calls a second, all answered.
  `adapter_spi_dma_is_busy` 7926 calls, none answered — the firmware is
  being told "not busy" by nobody.
- **Profile**: 83% firmware, 17% device model; inside the firmware,
  `app/Src` and `general-com` dominate.
- **Memory**: 22 frames deep, 2.0 KiB of host stack, nothing allocated.

The conclusion is not "the firmware is fine". It is: the measurement path
works end to end, the asynchronous SPI path is unmodelled and anything
depending on it is not being tested, and power is switched off in the
firmware's configuration rather than broken.

## What these tools cannot tell you

Worth stating plainly, because a tool that is trusted beyond its range is
worse than no tool:

- **Timing on the target.** Host time only. Proportions transfer, absolutes
  do not.
- **Stack bytes on the target.** Another ABI and another compiler. Depth
  and large buffers transfer; the total does not.
- **Whether an unmodelled function matters.** looper can tell you nothing
  answers it. Whether that invalidates your test is your judgement.
- **Anything about code it cannot read.** The audit says how many
  translation units it managed to parse. A clean report over half the
  sources is not a clean report, and it says so in its first line.
- **Timing of anything a library does.** Not instrumented, so its time lands
  in the self time of whatever called it.
