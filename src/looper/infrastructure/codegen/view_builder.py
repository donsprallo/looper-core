"""Construction of the generation view model from declarations and contract."""

from __future__ import annotations

from looper.domain.model.c_api import (
    AdapterModule,
    AdapterSurface,
    CExternData,
    CFunction,
    CParameter,
    CType,
    CTypeKind,
)
from looper.domain.model.contract import (
    AdapterContract,
    BufferLifetime,
    FunctionContract,
    ParameterContract,
    ParameterRole,
    WriteMoment,
)
from looper.infrastructure.codegen.binding_builder import build_binding
from looper.infrastructure.codegen.c_defaults import (
    default_return_expression,
    zero_value_expression,
)
from looper.infrastructure.codegen.c_naming import (
    declare,
    declare_parameter,
    generated_source_name,
    hook_type_name,
)
from looper.infrastructure.codegen.view_model import (
    BindingView,
    ExternDataView,
    FunctionView,
    ModuleView,
    OutputResetView,
    ParameterView,
    SurfaceView,
)

INITIALIZER_MACRO_PREFIX = "LOOPER_INIT_"
RESET_ROLES = frozenset({ParameterRole.OUTPUT, ParameterRole.INPUT_OUTPUT})


def build_surface_view(surface: AdapterSurface, contract: AdapterContract) -> SurfaceView:
    """Describe the simulation to generate for a parsed surface."""
    return SurfaceView(modules=tuple(_build_module(module, contract) for module in surface.modules))


def _build_module(module: AdapterModule, contract: AdapterContract) -> ModuleView:
    """Describe the generated source of one adapter header."""
    header_name = module.header_path.name
    return ModuleView(
        name=module.name,
        header_name=header_name,
        source_name=generated_source_name(header_name),
        functions=tuple(_build_function(function, contract) for function in module.functions),
        extern_data=tuple(_build_extern_data(symbol) for symbol in module.extern_data),
    )


def _build_function(function: CFunction, contract: AdapterContract) -> FunctionView:
    """Describe one generated function together with its hook."""
    function_contract = _contract_of(function, contract)
    return FunctionView(
        name=function.name,
        hook_type_name=hook_type_name(function.name),
        return_type=function.return_type.spelling,
        parameters=tuple(_build_parameter(parameter) for parameter in function.parameters),
        default_return=default_return_expression(function.return_type),
        output_resets=tuple(_build_resets(function, function_contract)),
        contract_notes=tuple(_build_notes(function, function_contract)),
        binding=_build_binding(function, contract),
    )


def _build_binding(function: CFunction, contract: AdapterContract) -> BindingView | None:
    """Describe what the function does without a hook, if the contract says.

    Raises:
        RoleError: If the role cannot be turned into code that compiles.
    """
    role = contract.role(function.name)
    return None if role is None else build_binding(function, role)


def _build_parameter(parameter: CParameter) -> ParameterView:
    """Describe one parameter declarator."""
    return ParameterView(
        name=parameter.name, declarator=declare_parameter(parameter.type, parameter.name)
    )


def _build_extern_data(symbol: CExternData) -> ExternDataView:
    """Describe one exported data symbol and its override macro."""
    return ExternDataView(
        name=symbol.name,
        declarator=declare(symbol.type.spelling, symbol.name),
        initializer_macro=f"{INITIALIZER_MACRO_PREFIX}{symbol.name}",
    )


def _contract_of(function: CFunction, contract: AdapterContract) -> FunctionContract:
    """Return the contract of a function, or an empty one when none exists."""
    if not contract.covers(function.name):
        return FunctionContract(function_name=function.name)
    return contract.function(function.name)


def _build_resets(
    function: CFunction, function_contract: FunctionContract
) -> list[OutputResetView]:
    """Describe the output parameters the default implementation zeroes."""
    return [
        OutputResetView(
            name=parameter.name,
            zero_expression=zero_value_expression(_pointee_of(parameter)),
        )
        for parameter in function.parameters
        if _needs_reset(parameter, function_contract)
    ]


def _needs_reset(parameter: CParameter, function_contract: FunctionContract) -> bool:
    """Report whether an output parameter is valid as soon as the call returns."""
    if not function_contract.covers(parameter.name):
        return False
    parameter_contract = function_contract.parameter(parameter.name)
    if parameter_contract.role not in RESET_ROLES:
        return False
    if parameter_contract.written_at is not WriteMoment.ON_RETURN:
        return False
    return parameter.type.kind is CTypeKind.POINTER and not parameter.type.is_opaque_handle


def _pointee_of(parameter: CParameter) -> CType:
    """Return the addressed type of a pointer parameter.

    Raises:
        ValueError: If the parameter is not a pointer.
    """
    pointee = parameter.type.pointee
    if pointee is None:
        raise ValueError(f"Parameter '{parameter.name}' is not a pointer")
    return pointee


def _build_notes(function: CFunction, function_contract: FunctionContract) -> list[str]:
    """Repeat the contract of each parameter as a documentation line."""
    return [
        f"{parameter.parameter_name}: {_describe(parameter)}"
        for parameter in function_contract.parameters
        if function.has_parameter(parameter.parameter_name)
    ]


def _describe(parameter: ParameterContract) -> str:
    """Describe one parameter contract in a single readable line."""
    parts = [parameter.role.value]
    if parameter.lifetime is not BufferLifetime.NOT_APPLICABLE:
        parts.append(parameter.lifetime.value)
    if parameter.written_at is not None:
        parts.append(f"written {parameter.written_at.value}")
    return ", ".join(parts)
