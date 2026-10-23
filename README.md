# looper-core

Software in the loop testing for HAL adapter based firmware projects.

`looper` reads a directory of hardware abstraction layer headers, generates a
host implementation of that same API, and lets a test or a graphical client
drive the simulated hardware over a protobuf control channel.

The premise is that a firmware project which talks to hardware through one
adapter layer can have that layer replaced, and that the firmware above it will
not know the difference.

## Try it

```console
$ uv sync
$ uv run looper-cli run examples/blinky/looper.toml
```

The example firmware starts and prints the port it listens on. Drive it from a
test, or watch it in a window: the graphical inspector lives in the
neighbouring `looper-gui` repository and attaches to the port this prints.

```console
$ cd ../looper-gui && uv run looper-gui --port 45771
```

## Use it on a real adapter

```console
$ uv run looper-cli analyze ../fw_in_adapter_pic32/Inc \
      -I ../embd-contracts/Inc -I ../fw_in_ioexpander/Inc

9 modules, 50 functions, 2 exported data symbols
57 declarations need a contract before generation:
  adapter_can_payload_tx_begin.data  [parameter_not_contracted]
  ...
```

A declaration says `const uint8_t *data`. It does not say whether the adapter
may keep that pointer after the call. For this function it may, and a
simulation that copies the buffer instead would compile, run, and hide exactly
the class of bug this tool exists to find. So it is written down once:

```toml
[adapter_can_payload_tx_begin]
transfer = { role = "context" }
data = { role = "input", lifetime = "borrowed" }
```

`looper-cli generate` refuses to run while anything is unspecified. Keep the
contract beside the rest of the simulation, in `sil/contract.toml`.

```console
$ uv run looper-cli generate ../fw_in_adapter_pic32/Inc \
      -I ../embd-contracts/Inc -I ../fw_in_ioexpander/Inc \
      --contract sil/contract.toml -o build/sil

11 files, 50 functions simulated
```

Describe the project once in a `looper.toml` and `looper-cli build` and
`looper-cli run` do generation, compilation and start up in one step:

```toml
[simulation]
name = "my-firmware"
headers = "../fw_in_adapter_pic32/Inc"
contract = "sil/contract.toml"
sources = ["src", "bsp"]
includes = ["Inc", "src"]
parse_includes = ["../embd-contracts/Inc", "../fw_in_ioexpander/Inc"]
```

Each generated function forwards to a hook a test may install, and applies a
documented default otherwise:

```c
looper_hooks_reset();
looper_hooks()->adapter_can_send_frame = count_frames;
```

## Commands

| Command | Purpose |
| --- | --- |
| `looper-cli` | `analyze`, `generate`, `build`, `run` |

The `looper-gui` repository adds a second command of the same name, which
attaches to a running simulation and inspects it. It does not start one,
because a simulation is your firmware compiled for the host.

## Documentation

```console
$ uv run --extra docs sphinx-build -b html -W docs docs/_build/html
```

Start with `docs/concepts.md` for the ideas and `docs/usage.md` for a
complete walkthrough. To put looper into a firmware project that already
exists, `docs/integrating.md` is the whole path, and `docs/building.md` has
every key of the build definition. The C runtime, the wire protocol and the
graphical inspector document themselves in their own repositories.

## Three projects

| Project | Is | Depends on |
| --- | --- | --- |
| `looper-rt` | the C runtime, the components and the protocol schema | nothing |
| `looper-core` | this: the library and `looper-cli` | `looper-rt` |
| `looper-gui` | the window that attaches to a running simulation | `looper-core` |

The dependencies run one way. `looper-rt` compiles wherever a firmware
project does and knows nothing of Python, which is what lets a project that
builds with CMake take the runtime without taking the tooling. Nothing here
imports Qt, which is what lets a build server install the tool without the
inspector.

The C sources are not in this repository. They arrive as `looper-rt`, an
installable distribution whose only Python is the module that locates them,
so a checkout and an installed wheel resolve to the same path.

## Layout

| Path | Contents |
| --- | --- |
| `src/looper/domain/` | declarations, contracts, simulation state, interfaces |
| `src/looper/application/` | use cases |
| `src/looper/infrastructure/` | libclang, code generation, contracts, the client |
| `src/looper/presentation/` | the command line tool |
| `examples/blinky/` | a complete worked example |

## Where the runtime comes from

`looper-rt` is not published yet, so it resolves from a neighbouring
checkout:

```toml
[tool.uv.sources]
looper-rt = { path = "../looper-rt", editable = true }
```

That is the only place naming where it lives. The examples that build with
CMake instead of `looper-cli` take the same default and accept
`-DLOOPER_RT_ROOT=<path>` to point elsewhere.

## Development

```console
$ uv run ruff format .
$ uv run ruff check .
$ uv run mypy
$ uv run pytest
```

`CLAUDE.md` holds the project rules. `docs/development.md` explains the test
layering and what to watch when changing the generator.
