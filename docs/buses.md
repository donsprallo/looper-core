# Buses and components

A firmware reaches most of its hardware through a bus: a converter on SPI, a
port expander on I2C, a terminal on UART, the rest of the vehicle on CAN.
None of that is visible through pins or measurement channels — what happens
is an exchange of bytes with something at an address.

So a bus is a model of its own, and what sits on it is a **component**.
looper ships a few, and a project writes its own the same way.

```python
from looper.infrastructure.ipc import ProtobufSimulationSession

session = ProtobufSimulationSession(port=45771)

for bus in session.read_buses():
    print(bus.identifier, bus.display_name, bus.kind.value, bus.bitrate_bps)
# 0 SPI1  spi  0
# 1 I2C1  i2c  0
# 2 CAN2  can  500000
# 3 UART1 uart 0

for component in session.read_components():
    print(component.bus, component.address.text, component.model)
# 0 0     as8510
# 1 0x20  mcp23x08
```

## The shape of it

```text
firmware → generated adapter hooks → binding → bus model → component
                                   (project)  (looper)    (looper or yours)
                                                  ↓
                                         trace → protocol → inspector
```

The **binding** is the only project specific part, and most of it is
generated. It exists because an adapter API is whatever the firmware's HAL
made it:

```c
bool adapter_i2c_read(void *context, uint8_t reg, uint8_t *data, size_t len, ...);
bool adapter_spi_transfer_blocking(void *context, const uint8_t *tx, uint8_t *rx, size_t len);
```

The I2C call names a *register*, not a device; the SPI call says nothing
about which chip select it meant, because the HAL identifies its device by
the context pointer. Neither shape is something a shipped component could
rely on. The binding resolves them — "this context is bus 0, chip select 0" —
and from there everything speaks in buses and addresses:

### Let the contract write it

The contract already says what a *parameter* means. A **role** says what a
*function* is, and that is enough for the generator to write the binding:

```toml
[roles.adapter_spi_transfer_blocking]
kind = "spi.transfer"
context = "context"
transmitted = "tx_data"
received = "rx_data"
length = "len"
```

What comes out is the fallback of the generated adapter — the path taken
when no hook is installed, so a project can still override it:

```c
    /* Contract: this is a transfer on an SPI bus. */
    {
        uint32_t looper_bus = 0u;
        uint32_t looper_address = 0u;

        if (looper_binding_resolve(
                context, LOOPER_BUS_KIND_SPI, &looper_bus, &looper_address
            )) {
            return looper_spi_transfer(
                looper_bus, (uint8_t)looper_address, tx_data, rx_data, len);
        }
    }
```

| Kind | What it becomes | Names |
| --- | --- | --- |
| `spi.transfer` | `looper_spi_transfer` | `context`, `transmitted`, `received`, `length` |
| `i2c.read` | `looper_i2c_read_register`, or `looper_i2c_exchange` without `register` | `context`, `data`, `length`, `register` |
| `i2c.write` | `looper_i2c_write_register`, or `looper_i2c_exchange` | as above |
| `uart.write` | `looper_uart_write` | `context`, `data`, `length` |
| `uart.read` | `looper_uart_read` | `context`, `data`, `length` |

Two things are checked before anything is written, because the alternative
is generated code the compiler rejects: every parameter a role names has to
exist on the function, and the function has to return `bool` — a bus answers
yes or no, and what anything else means is the adapter's own business.

**CAN has no role**, deliberately. A frame is a structure the contract would
have to describe field by field, and what a CAN controller mostly does is
apply acceptance filters, which is a decision rather than a translation.

### Where the device is

A role says what the call is; it cannot say which bus or which address,
because only the board knows. It says so once per device:

```c
looper_binding_bind(&g_spi_device, BOARD_SPI_BUS, BOARD_AS8510_CHIP_SELECT);
```

A board with one bus of a kind and one device on it need not say even that.
An unbound instance resolves to the only bus of the kind the call needs, and
to the only component attached to it, which is what most boards can rely
on:

```text
i2c  -> bus=1 address=0x20     (the port expander, and nothing else on I2C)
spi  -> bus=0 address=0x00     (the converter)
uart -> bus=3 address=0x00     (nothing attached)
```

A narrow guess: wrong only where a board has two of something, and there the
bind is one line.

## Why components are C

A component answers the firmware while the firmware is inside the call that
asked. A measurement front end such as the AS8510 converts **7944 times a
second**, and each conversion is an SPI frame; over a request and response
protocol that would be eight thousand round trips a second. It is not a
style preference.

The other two are not like that. On CAN and UART nobody is waiting inside a
call, so a peer there can be written in Python; see [Components written in
Python](#components-written-in-python).

## Writing one

A component is a struct of your own, a vtable of its bus's kind, and a call
to attach it. This is the whole of a device that answers one register:

```c
#include "looper_i2c.h"

typedef struct { uint8_t temperature; } thermometer_t;

static bool exchange(
    void *instance, const uint8_t *tx, size_t tx_length, uint8_t *rx, size_t rx_length
)
{
    thermometer_t *self = instance;

    if ((tx_length > 0u) && (tx[0] != 0x00u)) {
        return false;                      /* no such register */
    }
    if ((rx != NULL) && (rx_length > 0u)) {
        rx[0] = self->temperature;
    }
    return true;
}

static const looper_i2c_operations_t operations = {.exchange = exchange};

static thermometer_t thermometer = {.temperature = 21u};

looper_i2c_attach(BOARD_I2C_BUS, 0x48, "Thermometer", "lm75", &thermometer, &operations, NULL);
```

Two rules, and they are the whole contract:

- **Answer and return.** You are inside a call the firmware made. Do not
  block, and do not wait for anything outside the process.
- **Anything on your own clock goes in `run`.** The last argument to
  `attach` is called once per iteration of the firmware loop with the
  simulated time. A device that samples, times out, or answers after a
  delay does it there. `NULL` when you have nothing to do.

### What each kind asks for

| Kind | Operation | Address |
| --- | --- | --- |
| SPI | `transfer(instance, tx, rx, length)` | chip select |
| I2C | `exchange(instance, tx, tx_length, rx, rx_length)` | 7 bit address |
| UART | `receive(instance, port, data, length)` | port |
| CAN | `receive(instance, frame)` | base identifier |

I2C has one operation rather than three because every transaction is the
same shape underneath: address, write some bytes, read some bytes, either
half possibly empty. A plain write is a transaction with nothing read, a
register read is both halves at once.

UART and CAN answer by putting something back rather than by returning it —
`looper_uart_deliver` and `looper_can_inject` — because a peer replies when
it is ready, which is not necessarily inside the call.

## Publishing values

A component usually holds something worth seeing that never crosses its
bus: the voltage at a converter's inputs, the temperature a sensor is
pretending to measure. Those are **properties**, and a property is not a new
kind of thing — it is a value with a name and a unit that a client reads,
plots and sometimes drives, which is exactly what an analog channel already
is.

```c
looper_component_publish(
    bus, address, channel, "I_SENSE", "V", LOOPER_CHANNEL_DIRECTION_INPUT
);
```

So it appears on the Signals page, plots on the Scope, and is driven like
any other channel. What the component gets for free is the direction: a
property it *reads* is one a client drives, a property it *writes* is one a
client watches. The AS8510 publishes its two inputs this way, which is why
driving `I_SENSE` moves what the firmware measures:

```python
for component in session.read_components():
    print(component.display_name, component.properties)
# AS8510 (10, 11)
# IO expander ()
```

The inspector groups them under the component that published them.

## Modelling a flash that ships provisioned

A device model that answers the flash adapter out of a file gives a stored
configuration the property it has on a board: it survives a restart.

```c
/* The window beside whatever started the simulation. An environment
   variable points it elsewhere; an empty value keeps it in memory, which
   is what a test wants so one run cannot inherit the last one's settings. */
static const char *window_path(void);
```

A file alone is not enough, and the reason catches people out. A new file is
empty, and an empty flash is not what a board has. Firmware typically reads
its configuration **once, while it starts**, and builds its consumers from
what it found. A board that left a factory was provisioned past that point;
a fresh simulation was not. The visible symptom is a channel that is
registered and wired and still reads `no data`, and writing the
configuration afterwards does not help, because the consumer was already
built disabled.

So the simulation provisions it, from its entry point, between bringing the
board support up and starting the firmware:

```c
(void)provisioning_ensure_stored_configuration();
```

Three properties are worth copying:

- **Use the firmware's own code to assemble the record.** Product defaults,
  the firmware's own staging and validation calls, the firmware's own
  storage call. A record the device model assembled by hand is a record the
  firmware is entitled to reject, and the whole point is that it reads it
  back.
- **Do it once.** A window that already holds a configuration the firmware
  accepts is left exactly as it is, because the next thing anybody does on a
  bench is change a setting and restart to see whether it stuck. Deleting
  the window file is how a factory-fresh board comes back.
- **Expect the firmware to refuse the defaults.** Product defaults are often
  not a configuration the firmware will accept -- an unlimited output rate
  that its own bus-load check turns down, for instance. Provisioning that
  silently stores a declined record looks like it worked and changes
  nothing. Check the return value.

Provisioning switches on what the firmware has; it invents nothing. A
quantity the firmware does not compute still reads `no data` afterwards,
and that is the correct answer.

## Components written in Python

On CAN and UART nobody is waiting inside a call, so a peer there can live in
the client instead:

```python
from looper.application.components import BusComponent, ComponentHost


class Thermostat(BusComponent):
    def __init__(self, bus):
        super().__init__(bus, BusAddress(BusKind.CAN, 0x500), "Thermostat")

    def on_exchange(self, exchange):
        if exchange.address.value == 0x701:
            self.send(b"*")


with ComponentHost(session) as host:
    host.attach(Thermostat(bus=2))
    host.run(seconds=5.0)
```

It is listed like any other component, with the model `remote` so that a
reader can tell it is not in the simulation:

```text
bus 2  0x500  remote  Thermostat
```

**What it costs is latency.** Such a component learns what crossed from the
recording and answers on the next poll, so it reacts in tens of
milliseconds rather than microseconds. For a peer that would answer in
milliseconds anyway this changes nothing; for one the firmware times out on
in under a millisecond, write it in C.

SPI and I2C refuse one outright, for the reason the whole design turns on:

```python
Thermostat(bus=0, address=BusAddress(BusKind.SPI, 0))
# ValueError: The firmware is the master on a spi bus, so a client cannot
# take a peer's part there
```

## What looper ships

| Component | Bus | What it is |
| --- | --- | --- |
| `as8510` | SPI | current and voltage front end: register file, amplifier, conversions on its own clock |
| `mcp23x08` | I2C | eight bit port expander; its pins are registered in the pin model and appear beside the microcontroller's own |
| `tcp` | UART, CAN | carries the bus over a TCP port, so something outside the process can be the peer |
| `udp` | UART, CAN | the same over datagrams |

A project names what its board carries:

```toml
components = ["as8510", "mcp23x08"]
```

They are opt-in rather than always present, and for a reason worth knowing:
a direct build compiles what it is given while a linker keeps only what a
library is asked for, so compiling them all would make the two build paths
describe different programmes. The parity test in
`tests/integration/test_cmake_package.py` catches exactly that.

Through CMake the target is `looper::components`, linked for you by
`looper_add_simulation`.

### Keeping a component portable

A shipped component knows nothing about any board. What is board specific is
configuration, which the board passes in:

```c
static const looper_as8510_config_t config = {
    .reference_voltage_v = APP_MEASUREMENT_AS8510_REFERENCE_VOLTAGE_V,
    .read_input = read_sense,            /* where the voltages come from */
    .on_conversion_ready = raise_data_ready,  /* where the interrupt goes */
};
```

The chip's own properties — its register map, its gain steps, its full scale
— live in the component. The reference voltage, the inputs and what the
ready line is wired to are the board's, and the board supplies them.

## Taking a bus out of the process

A component answers the firmware from inside the simulation. A **bridge**
answers nothing: it carries what crosses a bus out to a socket and brings
back whatever is sent in. What is on the other end is not looper's business
— a terminal, a tool of your own, a second simulation, a test written in
something else.

```c
#include "looper_tcp.h"
#include "looper_udp.h"

looper_tcp_uart(BOARD_UART_BUS, 0u, "Console", 46100u);
looper_tcp_can(BOARD_CAN_BUS, 0x700u, "CAN gateway", 46101u);
looper_udp_can(BOARD_CAN_BUS, 0x701u, "CAN multicast", 46201u, "127.0.0.1", 46202u);
```

```toml
components = ["tcp", "udp"]
```

Then, from a shell:

```console
$ nc 127.0.0.1 46100        # the firmware's console output, and input back
```

A bridge is listed on the bus like any other peer, with `tcp` or `udp` as
its model, and everything that crosses it is in the recording as usual. A
bridge with nobody connected is not an error: it is a wire with nothing
plugged into it, which is what most wires are most of the time.

### Only UART and CAN

On SPI and I²C the firmware is inside the call, waiting. Nothing outside
the process can answer within that call, and a bridge that waited for a
socket would stop the firmware. UART and CAN have no such rule — a peer
there replies when it is ready — which is the same reason those two are the
kinds a Python component can take the part of.

### What goes over the wire

A UART bridge carries bytes as they are, because a serial line has no
frames to borrow. A CAN bridge carries frames in the layout
`looper_can_wire.h` writes down, six bytes of header and then the payload:

| Offset | Size | Meaning |
| --- | --- | --- |
| 0 | 4 | identifier, little endian |
| 4 | 1 | flags; bit 0 set for an extended frame |
| 5 | 1 | payload length, 0 to 8 |
| 6 | n | the payload |

Over TCP the frames follow one another in the stream; one that arrives in
two pieces is held until the rest comes. Over UDP one datagram is normally
one frame, and several in one datagram are read as well. The same bytes
either way, so a tool can speak to both.

A stream that falls out of step with the layout is dropped rather than
guessed at: once more bytes are waiting than the longest frame can hold
without a frame coming out of them, the buffer is thrown away.

### Where a UDP bridge sends

Give it a peer and it always sends there. Give it `NULL` and it answers
whoever last wrote to it, which is what makes this work with no
configuration at all:

```console
$ nc -u 127.0.0.1 46201
```

### Writing another transport

`looper_bridge.h` is the part that knows about buses, and it asks for two
functions: send these bytes, and take whatever has arrived. A transport
that is not a socket — a pipe, a file, a real serial port — is those two
functions and nothing else.

## Addresses

An address carries the kind it belongs to, and is checked against it. Chip
select 2 and I2C address 2 are not the same place, and a CAN identifier sent
as 11 bits is not the same identifier as the same value sent as 29:

```python
BusAddress(BusKind.I2C, 0x80)  # ValueError, wider than 7 bits
BusAddress(BusKind.CAN, 0x800)  # ValueError, wider than 11 bits
BusAddress(BusKind.CAN, 0x800, is_extended=True)  # fine
```

## Sending something in

Only two of the four kinds take a message from a client. On SPI and I2C the
firmware is the master: nothing crosses until it clocks, so to change what
it reads you change the component.

```python
session.send_bus_message(2, BusMessage(BusAddress(BusKind.CAN, 0x6FF), b"\x01\x02"))
session.send_bus_message(0, BusMessage(BusAddress(BusKind.SPI, 0), b"\x01"))
# ValueError: The firmware is the master on a spi bus, so nothing can be sent to it
```

Whether the firmware is actually given a CAN frame depends on its own
acceptance filters, which the controller's model applies. A frame they turn
away is still recorded, marked as not accepted, because a client that sent
something and saw no reaction needs to tell a filtered frame from a lost
one.

## The recording

Everything that crosses any bus is recorded on one timeline, read the way
the analog trace is read: a client remembers the sequence number it last saw
and asks for what came after.

```text
 4.3167 s  SPI1  TX  0       6  80 FF FF FF FF FF   00 0A 73 1A 1F 06
 4.3167 s  CAN2  TX  0x702   5  1F E7 26 43 40
 4.3169 s  CAN2  RX  0x123   2  DE AD                 refused
```

SPI and I2C fill both halves, because they answer in the same breath; a UART
run of bytes and a CAN frame fill one.

A bus can be fast, and the limit is worth knowing before you go looking for
a missing byte. An 8 kHz converter is 8000 transfers a second; the recording
keeps the most recent 4096 exchanges and one request carries at most 128.
A client is told where the recording now stands and continues from there, so
it is never left behind — but on a fast bus it sees a decimated picture
rather than every exchange.

## In the inspector

The **Buses** page lists what crossed, newest last. The selector narrows it
to one bus and shows that bus's rate and what is attached to it; the form
below sends a message, and says so plainly when the bus in view is one the
firmware masters.

## Reading a bus as a conversation

The Buses tab lists what crossed. Tick **As a conversation** and the same
records are arranged by who was talking: one column for the firmware, one
for every party it addressed, time running down, and a line for each
exchange.

```text
   1.3742              firmware ──── 80 FF FF FF FF FF ───▶ AS8510
                                ◀ ─ ─ 00 00 00 00 00 06 ─ ─
   1.3743   +135 us     firmware ──── 80 FF FF FF FF FF ───▶ AS8510
   1.3748   +5.3 ms     firmware ──── 40 12 ──────────────▶ chip select 1
```

A table answers *what happened* and leaves the reader to assemble *who said
what to whom* out of the direction column and the address column, row by
row. The ladder is that assembly done once.

Three things are meant to be visible without reading a word:

- **A line that goes out and does not come home** is an exchange with no
  answer. On SPI and I2C the answer comes back inside the same call and is
  drawn as a dashed line returning; a request without one stands out.
- **An exchange nothing took is red.** `accepted` is false when no component
  answered, or when a controller's filters turned a frame away.
- **A column nothing ever took from is drawn in red**, and named under the
  diagram. That is the single most useful thing a bus view can point at, and
  in a table it is spread over every row the address appears in.

A column is named after the component that sits there -- `AS8510` rather
than `0` -- and after the kind of place when nothing does: `chip select 1`,
`identifier 0x702`. On a broadcast bus every identifier gets its own column,
which makes a firmware's signal map visible as it is being sent.

The rows are **evenly spaced however far apart in time they were**, because
a ladder is read for its order and a burst would otherwise be unreadable.
That is why each row carries the gap since the last one: the clock is
written rather than drawn. For the clock drawn to scale, use the
{gui}`Timeline <gui.html>` tab, where the same exchanges sit on a shared ruler
beside the curves and the pins.

Reading a conversation costs a second pass over the trace, so it happens
only while the view is open.

## The protocol

| Command | Reads | Writes |
| --- | --- | --- |
| `COMMAND_LIST_BUSES` | every registered bus | |
| `COMMAND_LIST_COMPONENTS` | every attached component | |
| `COMMAND_READ_BUS_TRACE` | exchanges after a sequence | |
| `COMMAND_CLEAR_BUS_TRACE` | | the recording |
| `COMMAND_SEND_BUS_MESSAGE` | | one message onto a bus |
| `COMMAND_ATTACH_COMPONENT` | | takes a peer's part on a bus |
| `COMMAND_DETACH_COMPONENT` | | gives it up |

The bus recording is numbered independently of the analog trace, so its
continuation point comes back in `next_bus_sequence`.
