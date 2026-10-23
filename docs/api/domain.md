# Domain

The framework free core. Nothing in this layer imports a third party package.

## Adapter surface

```{eval-rst}
.. automodule:: looper.domain.model.c_api.c_type
.. automodule:: looper.domain.model.c_api.c_parameter
.. automodule:: looper.domain.model.c_api.c_function
.. automodule:: looper.domain.model.c_api.c_record
.. automodule:: looper.domain.model.c_api.c_enum
.. automodule:: looper.domain.model.c_api.c_extern_data
.. automodule:: looper.domain.model.c_api.adapter_module
.. automodule:: looper.domain.model.c_api.adapter_surface
.. automodule:: looper.domain.model.c_api.validation
```

## Contract

```{eval-rst}
.. automodule:: looper.domain.model.contract.parameter_contract
.. automodule:: looper.domain.model.contract.function_contract
.. automodule:: looper.domain.model.contract.adapter_contract
.. automodule:: looper.domain.model.contract.coverage
```

## Simulation state

```{eval-rst}
.. automodule:: looper.domain.model.simulation.pin_identifier
.. automodule:: looper.domain.model.simulation.gpio_pin
.. automodule:: looper.domain.model.simulation.simulation_time
.. automodule:: looper.domain.model.simulation.time_mode
```

## Generated artifacts

```{eval-rst}
.. automodule:: looper.domain.model.codegen.generated_artifact
```

## Profiling

```{eval-rst}
.. automodule:: looper.domain.model.sources.function_origin
.. automodule:: looper.domain.model.sources.source_layout
.. automodule:: looper.domain.model.profile.measured_function
.. automodule:: looper.domain.model.profile.profiled_function
.. automodule:: looper.domain.model.profile.profile_report
.. automodule:: looper.domain.model.profile.measured_path
.. automodule:: looper.domain.model.profile.flame
.. automodule:: looper.domain.services.flame_tree
.. automodule:: looper.domain.model.firmware.function_symbol
```

## Memory

```{eval-rst}
.. automodule:: looper.domain.model.memory.static_memory
.. automodule:: looper.domain.model.memory.stack_usage
.. automodule:: looper.domain.model.memory.heap_usage
.. automodule:: looper.domain.model.memory.heap_reading
.. automodule:: looper.domain.model.firmware.static_symbol
.. automodule:: looper.domain.services.static_memory
.. automodule:: looper.domain.services.symbol_index
```

## Timelines

```{eval-rst}
.. automodule:: looper.domain.model.timeline.time_window
.. automodule:: looper.domain.model.timeline.event
.. automodule:: looper.domain.model.timeline.lane
.. automodule:: looper.domain.model.timeline.timeline
.. automodule:: looper.domain.services.cadence
.. automodule:: looper.domain.model.measurement.distribution
.. automodule:: looper.domain.model.simulation.adapter_call
.. automodule:: looper.domain.model.simulation.pin_change
.. automodule:: looper.domain.services.level_runs
.. automodule:: looper.domain.services.decimation
.. automodule:: looper.domain.services.conversation
```

## Analysis

```{eval-rst}
.. automodule:: looper.domain.model.analysis.finding
.. automodule:: looper.domain.model.analysis.call_site
.. automodule:: looper.domain.model.analysis.firmware_usage
```

## Services

```{eval-rst}
.. automodule:: looper.domain.services.module_naming
.. automodule:: looper.domain.services.contract_coverage
.. automodule:: looper.domain.services.project_inspection
```

## Interfaces

```{eval-rst}
.. automodule:: looper.domain.repositories
.. automodule:: looper.domain.ports
.. automodule:: looper.domain.ports.progress
```
