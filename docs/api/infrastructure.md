# Infrastructure

Concrete implementations of the abstract domain interfaces.

## Header parsing

```{eval-rst}
.. automodule:: looper.infrastructure.parsing.parse_options
.. automodule:: looper.infrastructure.parsing.libclang_surface_repository
.. automodule:: looper.infrastructure.parsing.declaration_collector
.. automodule:: looper.infrastructure.parsing.declaration_reader
.. automodule:: looper.infrastructure.parsing.type_mapper
.. automodule:: looper.infrastructure.parsing.clang_library
.. automodule:: looper.infrastructure.parsing.errors
```

## Contracts

```{eval-rst}
.. automodule:: looper.infrastructure.contracts.toml_contract_repository
.. automodule:: looper.infrastructure.contracts.errors
```

## File system

```{eval-rst}
.. automodule:: looper.infrastructure.filesystem.artifact_repository
```

## Code generation

```{eval-rst}
.. automodule:: looper.infrastructure.codegen.c_simulation_generator
.. automodule:: looper.infrastructure.codegen.view_model
.. automodule:: looper.infrastructure.codegen.view_builder
.. automodule:: looper.infrastructure.codegen.c_naming
.. automodule:: looper.infrastructure.codegen.c_defaults
```

## Building

```{eval-rst}
.. automodule:: looper.infrastructure.build.compiler_builder
.. automodule:: looper.infrastructure.build.compiler_invocation
.. automodule:: looper.infrastructure.build.translation_units
.. automodule:: looper.infrastructure.build.freshness
.. automodule:: looper.infrastructure.build.depfile
.. automodule:: looper.infrastructure.build.project_sources
.. automodule:: looper.infrastructure.build.errors
```

## Debug information

```{eval-rst}
.. automodule:: looper.infrastructure.debug.errors
.. automodule:: looper.infrastructure.debug.parsed_builds
.. automodule:: looper.infrastructure.debug.dwarf_functions
.. automodule:: looper.infrastructure.debug.dwarf_statics
.. automodule:: looper.infrastructure.debug.dwarf_sources
.. automodule:: looper.infrastructure.profile_layout
.. automodule:: looper.infrastructure.build.instrumentation
```

## Project inspection

```{eval-rst}
.. automodule:: looper.infrastructure.analysis.firmware_scanner
.. automodule:: looper.infrastructure.analysis.call_arguments
.. automodule:: looper.infrastructure.analysis.libclang_usage_reader
```

## Control channel

```{eval-rst}
.. automodule:: looper.infrastructure.ipc.protobuf_session
.. automodule:: looper.infrastructure.ipc.framing
.. automodule:: looper.infrastructure.ipc.translation
.. automodule:: looper.infrastructure.ipc.errors
```
