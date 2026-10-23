# Development

## Checks

Every change has to pass all four. They run in seconds.

```console
$ uv run ruff format .          # formatting
$ uv run ruff check .           # lint, including import order
$ uv run mypy                   # strict type checking
$ uv run pytest                 # tests
```

`ruff check` carries the `I` rule set, so import sorting is part of linting
rather than a separate tool. `ruff check --fix .` sorts them in place.

Documentation is built with warnings treated as errors, which keeps broken
references from accumulating:

```console
$ uv run --extra docs sphinx-build -b html -W docs docs/_build/html
```

## Project rules

`CLAUDE.md` is the source of truth. The two limits worth repeating:

- A function body is at most 20 lines. Docstrings do not count.
- A module is at most 250 lines; beyond that it gets split.

Full typing is mandatory and `mypy` runs in strict mode. Types belong in
signatures and are never repeated in docstrings — Sphinx reads them from the
annotations.

## Tests

Tests mirror the layer they cover. The inspector keeps its own suite in the
`looper-gui` repository.

| Directory | Covers |
| --- | --- |
| `tests/domain/` | invariants of the model, pure and fast |
| `tests/application/` | use cases against test doubles |
| `tests/infrastructure/` | the real libclang front end and the real generator |
| `tests/presentation/` | the command line tool |
| `tests/integration/` | the whole chain against a running simulation |

The most important test is `test_generated_code_compiles.py`. Generated code is
C, so the only honest check is a C compiler: the test parses a header, generates
from it, builds the result with `-Wall -Wextra -Werror` together with a program
that installs a hook, and runs it. It is skipped when no compiler is on `PATH`.

A unit test asserting on generated *text* can pass while the output does not
compile. Keep the compile test the final word.

`tests/integration/test_blinky_simulation.py` goes one step further: it builds the example firmware, starts it as a process, and drives it over the control
protocol. It is also the only check that the two protobuf implementations agree,
since the hand written C encoder and the reference Python runtime meet only on
the wire. Both are skipped when no compiler is on `PATH`.

## The C side

The runtime is built and checked by the same example build:

```console
$ uv run looper-cli build examples/blinky/looper.toml
```

It compiles the runtime, the generated sources and the example firmware with
`-Wall -Wextra -Werror`, so a warning anywhere fails the build.

After changing `proto/looper_control.proto`, regenerate the Python bindings and
update the matching field numbers in
`src/looper/runtime/src/looper_protocol_fields.h`:

```console
$ uv run python scripts/generate_protocol.py
```

The generated Python modules are committed and excluded from linting and type
checking.

## Adding a generated artifact

1. Add a template under `infrastructure/codegen/templates/`. Templates contain
   layout only.
2. Extend the view model in `view_model.py` and build it in `view_builder.py`.
   Every decision — declarators, defaults, resets — is made in Python where it
   is type checked and testable.
3. Render it in `CSimulationGenerator.generate`.
4. Assert on the rendered text, then extend the compile test.

## The runtime layout

| File | Responsibility |
| --- | --- |
| `looper_clock.c` | both time sources |
| `looper_gpio_model.c` | the pin registry |
| `looper_journal.c` | the call ring buffer |
| `looper_pb.c` | protobuf wire primitives |
| `looper_protocol_fields.h` | field numbers, in one place |
| `looper_protocol_decode.c` | requests off the wire |
| `looper_protocol_encode.c` | responses onto it |
| `looper_commands.c` | what each command does |
| `looper_server.c` | sockets and framing only |
| `looper_app.c` | the entry point every simulation shares |

Two CMake targets come out of it: `looper::runtime` is the model, the
protocol and the server, and says nothing to any stream; `looper::app` adds
the entry point, which has to print. `cmake/LooperSimulation.cmake` declares
a simulation from a build definition.
| `looper_image.c` | where the process was loaded |
| `looper_watch.c` | the watched variable registry |
| `looper_watch_memory.c` | firmware memory to and from a double |

Changing a field number in the schema means changing the matching `#define` in
`looper_protocol_fields.h`. Nothing else in the runtime knows them.

`tests/infrastructure/ipc/test_protocol_fields.py` reads both files as text
and fails if they disagree, if the runtime is missing a field, or if it still
defines one the schema has dropped. It needs no compiler and no running
simulation, which is the point: a number that moved on one side only is not a
parse error but a value read into the wrong field, and the integration test
would only notice it for the fields it happens to exercise.

Where the C side spells a name differently from the schema, the difference is
listed in `tests/infrastructure/ipc/protocol_schema.py` rather than inferred
from a rule, so that a new one has to be written down.

## Layer boundaries

The dependency rule is enforced by review, except at the seam with the
inspector, which a test in that project checks. Things to watch:

- `domain/` imports nothing but the standard library. No `clang`, no `pydantic`,
  no `jinja2`, no `PySide6`.
- Use cases depend on the abstract interfaces in `domain/repositories.py` and
  `domain/ports.py`, never on a concrete implementation. Wiring happens in the
  presentation layer.
- Nothing here imports Qt or the inspector. The dependency runs one way,
  which is what lets the inspector be a project of its own. The check lives
  in the client, where both sides are visible:
  `tests/test_inspector_boundary.py` in `looper-gui` reads the installed
  library and fails on an import crossing back.
- A refusal has a type of its own, `SimulationRejectedError`, and it lives
  with the port rather than with the adapter. A client has to tell "the
  simulation will not do that" from "the simulation has stopped answering",
  and it should not have to know which adapter it was given to do so.
