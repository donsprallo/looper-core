# Concepts

Seven ideas carry the whole tool. Everything else follows from them.

## The adapter surface

A firmware project that talks to hardware through a hardware abstraction layer
has exactly one place where it touches the silicon: the adapter. In
`fw_in_adapter_pic32` that place is nine headers in `Inc/` — 50 functions and
two exported data symbols. The firmware above it never includes a Harmony
header.

That boundary is what makes software in the loop testing possible. Replace the
adapter and the firmware above it does not know the difference.

`looper` reads those headers with the libclang front end and turns them into an
**adapter surface**: modules, functions, parameters, records, enumerations, and
exported data.

```console
$ looper-cli analyze ../fw_in_adapter_pic32/Inc -I ../embd-contracts/Inc
9 modules, 50 functions, 2 exported data symbols
```

### Exported data is part of the surface

Adapter headers export more than functions:

```c
extern const embd_gpio_interface_t mcu_gpio_interface;
```

A generated simulation that defines all 50 functions but neither interface
table does not link. Data symbols are therefore modelled next to functions, not
treated as parsing debris.

## The contract

A declaration states types. It does not state meaning:

```c
adapter_can_result_t adapter_can_payload_tx_begin(
    adapter_can_payload_tx_t *transfer,
    uint8_t fifo_index,
    uint32_t id,
    adapter_can_id_format_t id_format,
    const uint8_t *data,
    size_t length
);
```

Three questions the signature leaves open:

- Is `transfer` instance state the adapter keeps between calls, or a payload?
- May the adapter keep `data` after the call returns?
- When does the caller get to read a result?

For this function the header documentation answers the second one: *"The payload
buffer is referenced, not copied. It must remain valid until the transfer
completes or is cancelled."* A simulation that copies the buffer instead would
compile, run, and pass a naive test — and hide the exact class of bug that
software in the loop testing exists to find.

So it is written down, once, per parameter:

```toml
[adapter_can_payload_tx_begin]
transfer = { role = "context" }
data = { role = "input", lifetime = "borrowed" }
```

| Key | Values | Meaning |
| --- | --- | --- |
| `role` | `input`, `output`, `input_output`, `callback`, `context` | direction of data flow |
| `lifetime` | `copied`, `borrowed` | whether the adapter may retain the pointer |
| `written_at` | `on_return`, `on_callback` | when an output buffer becomes valid |

`context` marks caller owned instance state — `spi_context_t *context`,
`adapter_can_t *adapter` — as opposed to payload memory. Nothing in the C type
distinguishes the two, which is precisely why a human writes it down.

Every pointer to a concrete type and every callback needs an entry. Opaque
`void *` handles do not: they cannot be anything but a context.

### A contract can also say what a function *does*

Everything above says what a parameter *means*, which is enough to generate
a stub. A **role** says what a function is:

```toml
[roles.adapter_spi_transfer_blocking]
kind = "spi.transfer"
context = "context"
transmitted = "tx_data"
received = "rx_data"
length = "len"
```

With that, the generated function does not merely report that it did
nothing — it carries the transfer out against the bus model. That is the
binding a project would otherwise write by hand for every adapter it
simulates. See [Buses and components](buses.md).

### The contract is checked, not assumed

`analyze` lists what is still missing, and `generate` refuses to run while
anything is:

```text
57 declarations need a contract before generation:
  adapter_can_payload_tx_begin.data  [parameter_not_contracted]
```

Entries naming a function or parameter that no longer exists are reported too,
so the contract cannot drift away from the headers unnoticed.

## The hook table

The generated simulation is not a mock framework. It is one C function per
adapter function, each forwarding to a **hook** the test may install:

```c
demo_result_t adapter_demo_receive(demo_frame_t *frame)
{
    const looper_hooks_t *looper_table = looper_hooks();

    if (looper_table->adapter_demo_receive != NULL) {
        return looper_table->adapter_demo_receive(frame);
    }

    /* Contract: frame is written before this call returns. */
    if (frame != NULL) {
        *frame = (demo_frame_t){0};
    }

    return (demo_result_t)0;
}
```

A test installs behaviour by assigning a function pointer:

```c
static demo_result_t fake_receive(demo_frame_t *frame)
{
    frame->id = 0x2A;
    return DEMO_OK;
}

looper_hooks_reset();
looper_hooks()->adapter_demo_receive = fake_receive;
```

The table is plain C with no allocation and no registry, so it works the same
way from a C test, from a device model, and later from the process that bridges
to a Python client. Writing the generator once was the point.

## Default behaviour

A hook that is not installed is not an error. The generated function applies a
documented default, and every default is the **zero value** of its type —
unless the contract gave the function a role, in which case the default is
to do what the role says.

| Return type | Default |
| --- | --- |
| `void` | returns immediately |
| `bool` | `false` |
| integer, floating point | `0` |
| enumeration | `(type)0` |
| pointer | `NULL` |
| struct, union | `(type){0}` |

`bool` returning `false` is a deliberate choice: an adapter that has not been
implemented reports that it did nothing, rather than silently claiming success.

The contract adds one behaviour on top. An output parameter marked
`written_at = "on_return"` is zeroed before the default returns, so the caller
never reads uninitialised memory:

```c
/* Contract: frame is written before this call returns. */
if (frame != NULL) {
    *frame = (demo_frame_t){0};
}
```

This is the contract doing real work rather than only documenting intent.

### Exported data gets an override seam

An exported symbol is defined through a macro, so a test can supply real
content without editing generated code:

```c
#ifndef LOOPER_INIT_mcu_gpio_interface
#define LOOPER_INIT_mcu_gpio_interface {0}
#endif

const embd_gpio_interface_t mcu_gpio_interface = LOOPER_INIT_mcu_gpio_interface;
```

Build with `-DLOOPER_INIT_mcu_gpio_interface='{ .set = my_set, .get = my_get }'`
to wire it up.

## The journal

Hooks answer what an adapter does when the firmware calls it. The other half of
a test is whether it was called at all:

```c
looper_journal_clear();
run_one_firmware_cycle();
assert(looper_journal_count_of("adapter_can_send_frame") == 1u);
```

Generated adapters record themselves, but only when compiled with
`-DLOOPER_JOURNAL`. Without that define the macro expands to nothing and the
generated code keeps its property of having no runtime dependency at all.

A client reads the same journal over the control channel, which is how a Python
test asserts on firmware behaviour without a line of C.

## The device model

A hook can do anything. In practice most hooks do the same thing: map an
adapter call onto simulated state.

```c
static void model_gpio_set(blinky_pin_t pin, blinky_pin_state_t state)
{
    looper_gpio_write(pin, level_for(pin, state));
}
```

That mapping is the device model. It is the one piece a project writes by hand,
it is ordinary C, and a test that wants different behaviour simply installs its
own hooks over the top. See {rt}`The runtime <runtime.html>`.

## Time

Simulated time has two sources, chosen when the firmware starts.

**Virtual time** advances only once every firmware thread is blocked. Test runs
become deterministic and independent of host load, and a firmware timeout of
thirty seconds costs microseconds of wall clock.

**Real time** follows the host clock. Interactive inspection and a graphical
client need it, because a human observer cannot be part of the condition that
lets a virtual clock advance. The model states this rather than leaving it to a
comment:

```python
from looper.domain.model.simulation import TimeMode

TimeMode.REAL_TIME.supports_interactive_inspection  # True
TimeMode.VIRTUAL.supports_interactive_inspection  # False
```

## Known differences from hardware

A simulation is not the silicon, and the places where it differs are worth
knowing:

- `panic()` is declared never to return. The generated default *does* return,
  because a generated function cannot decide how a test should fail. Install a
  hook that calls `abort()` when a test needs the real semantics.
- Interrupt driven adapters complete through a callback. Without a hook nothing
  ever calls it, so a firmware state machine waiting for completion waits
  forever. That is correct behaviour for an uninstalled hook, not a defect.
- Timing defaults to zero. `millis()` without a hook always answers `0`.
- The example firmware advances its own virtual clock by one millisecond per
  idle loop iteration. A pure polling loop never blocks, so without that nudge
  a virtual clock would stand still and the demo would look frozen. Real
  firmware that calls a blocking delay does not need it.
