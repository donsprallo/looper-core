# Architecture

`looper` follows the dependency rule of clean architecture: every dependency
points inwards, towards the domain.

## Projects

The outermost ring is cut along a repository boundary rather than a directory
one. This project, `looper-core`, is the library: the domain, the use cases,
the adapters and the command line tool. `looper-gui` is one client of it.

| Project | Imports as | Depends on |
| --- | --- | --- |
| `looper-core` | `looper` | its own dependencies only |
| `looper-gui` | `looper_gui` | `looper-core`, PySide6 |

The dependency runs one way: nothing here imports Qt or the inspector, so a
build server that only runs the command line tool installs the library alone.
What the two entry points share is how they name themselves, and that lives
in the library they both depend on.

Because the check has to see both sides, it lives in the client:
`tests/test_inspector_boundary.py` in `looper-gui` reads the installed
library and fails if anything in it reaches for Qt or for the inspector.
A development checkout has both installed side by side and would not
otherwise notice an import crossing back.

## Layers

| Layer | Responsibility | Depends on |
| --- | --- | --- |
| `domain` | Declarations, contracts, simulation state, abstract interfaces | the standard library only |
| `application` | Use cases such as analyse, generate, build, drive | `domain` |
| `infrastructure` | libclang parsing, C code generation, contract files, protobuf transport | `application`, `domain` |
| `presentation` | the command line tool | `application` |

The inspector sits in the same ring as `presentation`, in a repository of
its own, and depends on `application` exactly as the command line tool does.

The domain layer has no third party imports at all. Parsing C is an
infrastructure concern, so `libclang` never appears in the model; the parser
implements an abstract repository and hands back value objects.

## Model areas

### Adapter surface

The declarations read from the adapter headers. The surface owns invariants
that a single header cannot check, most importantly that function names stay
unique across all modules because they share one link time namespace.

Data symbols are modelled explicitly next to functions. Adapter headers export
interface tables such as `mcu_gpio_interface`, and a generated adapter that
defines every function but no table does not link.

### Contract

Semantics that a declaration cannot express. Whether an adapter may retain a
pointer it was handed is stated in prose in the header documentation, never in
the signature. Guessing it wrong produces a simulation that behaves plausibly
and is subtly wrong, so the contract is written by hand and the coverage
service reports every parameter that still lacks one.

### Simulation state

What a client observes and manipulates while the firmware runs: pins, their
polarity, and elapsed firmware time.

Pin identity is the opaque pin number the firmware uses. A display label can be
attached for a human reader but is excluded from comparison, so labelling a pin
never changes which pin it is.

## Time

Simulated time has two sources, selected when the firmware starts.

`VIRTUAL` advances only once every firmware thread is blocked. Test runs are
deterministic and a thirty second firmware timeout costs microseconds of wall
clock.

`REAL_TIME` follows the host clock. Interactive inspection and the graphical
interface require it, because a human observer cannot be part of the condition
that lets a virtual clock advance.

## How a request flows

`looper-cli generate` is the longest path through the layers and shows the rule at
work:

1. **Presentation** parses the command line and constructs the concrete
   repositories, the generator, and the use case.
2. **Application** (`GenerateSimulation`) loads the surface and the contract
   through abstract interfaces, evaluates coverage, and refuses if the contract
   is incomplete.
3. **Domain** (`evaluate_contract_coverage`) decides what counts as a gap. It
   knows nothing about files, compilers or templates.
4. **Infrastructure** (`CSimulationGenerator`) renders the artifacts, and
   `FileSystemArtifactRepository` writes them.

Nothing in step 2 or 3 knows that libclang parses the headers, that the contract
is TOML, or that the output is C. Swapping any of those is an implementation
change in one place.

## Generation is split in two

Rendering C is not one step but two, deliberately:

`view_builder.py` makes every decision — how a declarator is spelled, what a
function returns without a hook, which output parameters are zeroed — and
produces a plain value object. The Jinja templates then contain layout only.

The reason is testability. Decisions in Python are type checked by `mypy` and
unit tested directly; decisions inside a template are neither.

## Two sides of one system

Half of looper is Python and half is C, and the boundary is the generated code.

```text
  headers  ->  looper (Python)  ->  generated C  ->  firmware binary
                                         |
                                   looper runtime (C)
                                         |
                                  control protocol
                                         |
  Python client / Qt inspector  <--------+
```

The Python side never runs firmware; the C side never parses anything. They
meet twice: in the generated sources, and on the wire.

## Where the port abstraction pays

`SimulationSession` in `domain/ports.py` is the only thing the use cases know
about a running simulation. Three consequences follow:

- `ObserveSimulation` and `DrivePin` are tested against a fake session, with no
  process, no socket and no compiler.
- The Qt inspector calls those same use cases. It contains no protobuf, no
  socket handling, and no rule about which pins may be driven.
- Replacing TCP with a pipe, or protobuf with something else, changes one class
  in `infrastructure/ipc/` and nothing else. Including how it says no: a
  refusal is `SimulationRejectedError`, which belongs to the port, so a client
  that tells a refusal from a breakage does not thereby learn which adapter it
  was handed.

The same holds on the generation side: `AdapterSimulationGenerator` is a port,
so the C generator is an implementation detail of one package.

## What is deliberately not abstracted

The runtime is C and is not hidden behind an interface. A simulation links it
directly. An abstraction there would buy nothing: the only consumer is
generated code and a hand written device model, both of which are C already.
