# looper

Software in the loop testing for HAL adapter based firmware projects.

`looper` reads a directory of hardware abstraction layer headers, generates a
host implementation of that same API, builds the firmware against it, and lets
a test or a graphical client drive the simulated hardware over an inter process
channel.

```console
$ looper-cli analyze  ../fw_in_adapter_pic32/Inc -I ../embd-contracts/Inc
9 modules, 50 functions, 2 exported data symbols

$ looper-cli generate ../fw_in_adapter_pic32/Inc -I ../embd-contracts/Inc \
      --contract sil/contract.toml -o build/sil
11 files, 50 functions simulated
```

New here? Read [Concepts](concepts.md) first — it explains why a parsed
declaration is not enough and what the contract adds. The [User
guide](usage.md) walks through a complete run, starting with an example you can
build in one command.

| Page | Covers |
| --- | --- |
| [Concepts](concepts.md) | the adapter surface, the contract, hooks, time |
| [User guide](usage.md) | installation, the commands, troubleshooting |
| [Building a simulation](building.md) | the build definition, build and run |
| [Bringing looper into a firmware project](integrating.md) | the whole path for a project that already exists |
| {rt}`The runtime <runtime.html>` | the C clock, pin model, journal and server |
| {rt}`The control protocol <protocol.html>` | the wire format, in a project of its own |
| {gui}`The inspector <gui.html>` | the graphical client, a project of its own |
| [Firmware variables](variables.md) | reading, watching and writing globals |
| [Signals](signals.md) | driving the analog inputs a simulation offers |
| [Buses and components](buses.md) | SPI, I2C, UART and CAN; writing your own device |
| [Analysing a firmware](analysing.md) | which question each tool answers, and what the answer means |
| [Checking a simulation](checking.md) | the audit, the timing and memory pages, expectations in pytest |
| [Architecture](architecture.md) | the layering and why generation is split |
| [Development](development.md) | checks, tests, project rules |

```{toctree}
:maxdepth: 2
:caption: Contents

concepts
usage
building
integrating
variables
signals
buses
analysing
checking
architecture
development
api/domain
api/application
api/infrastructure
api/presentation
```

## Indices

- {ref}`genindex`
- {ref}`modindex`
