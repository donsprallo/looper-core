"""Render ready description of the code that is about to be generated.

The templates contain layout only. Every decision -- what a declarator looks
like, what a function returns without a hook, which output buffers have to be
zeroed -- is made here, where it can be type checked and tested.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ParameterView:
    """One parameter of a generated function.

    Attributes:
        name: Parameter name.
        declarator: Complete C declarator, name included.
    """

    name: str
    declarator: str


@dataclass(frozen=True)
class OutputResetView:
    """An output parameter the default implementation zeroes before returning.

    Attributes:
        name: Parameter name.
        zero_expression: Compound literal that zeroes the addressed value.
    """

    name: str
    zero_expression: str


@dataclass(frozen=True)
class BindingView:
    """What a generated function does when the contract says it uses a bus.

    Without a role a function without a hook reports that it did nothing.
    With one it carries the call out, which is the binding a project would
    otherwise write by hand.

    Attributes:
        description: What the contract said, repeated as a comment.
        instance: Parameter holding the context that says which device.
        bus_kind: Runtime enumerator of the kind of bus.
        call: The complete call, in terms of looper_bus and looper_address.
        header: Runtime header the call needs.
    """

    description: str
    instance: str
    bus_kind: str
    call: str
    header: str


@dataclass(frozen=True)
class FunctionView:
    """One adapter function, its hook, and its behaviour without a hook.

    Attributes:
        name: Adapter function name.
        hook_type_name: Name of the hook function pointer type.
        return_type: Return type as declared.
        parameters: Parameters in source order.
        default_return: Expression returned without a hook, or ``None`` for void.
        output_resets: Output parameters zeroed before returning.
        contract_notes: Contract lines repeated as documentation on the hook.
        binding: What to do without a hook when the contract gives a role.
    """

    name: str
    hook_type_name: str
    return_type: str
    parameters: tuple[ParameterView, ...] = field(default_factory=tuple)
    default_return: str | None = None
    output_resets: tuple[OutputResetView, ...] = field(default_factory=tuple)
    contract_notes: tuple[str, ...] = field(default_factory=tuple)
    binding: BindingView | None = None

    @property
    def answered_expression(self) -> str:
        """Whether anything implements this call, as C the adapter evaluates.

        A role makes the answer unconditional, because the generated
        binding is always there. Without one it depends on whether a device
        model installed a hook, which is only knowable while running.
        """
        if self.binding is not None:
            return "true"
        return f"looper_hooks()->{self.name} != NULL"

    @property
    def parameter_list(self) -> str:
        """Parameter declarators as they appear in a signature."""
        if not self.parameters:
            return "void"
        return ", ".join(parameter.declarator for parameter in self.parameters)

    @property
    def argument_list(self) -> str:
        """Parameter names as they appear when forwarding to the hook."""
        return ", ".join(parameter.name for parameter in self.parameters)


@dataclass(frozen=True)
class ExternDataView:
    """One exported data symbol the generated adapter has to define.

    Attributes:
        name: Symbol name.
        declarator: Complete C declarator, name included.
        initializer_macro: Macro a test may define to supply real content.
    """

    name: str
    declarator: str
    initializer_macro: str


@dataclass(frozen=True)
class ModuleView:
    """Everything the generated source of one adapter header contains.

    Attributes:
        name: Short module name.
        header_name: File name of the adapter header to include.
        source_name: File name of the generated source.
        functions: Functions to implement.
        extern_data: Data symbols to define.
    """

    name: str
    header_name: str
    source_name: str
    functions: tuple[FunctionView, ...] = field(default_factory=tuple)
    extern_data: tuple[ExternDataView, ...] = field(default_factory=tuple)

    @property
    def binding_headers(self) -> tuple[str, ...]:
        """Runtime headers the generated bindings need, without repeats."""
        headers = [
            function.binding.header for function in self.functions if function.binding is not None
        ]
        return tuple(sorted(set(headers)))


@dataclass(frozen=True)
class SurfaceView:
    """The complete simulation to generate.

    Attributes:
        modules: Modules in surface order.
    """

    modules: tuple[ModuleView, ...] = field(default_factory=tuple)

    @property
    def functions(self) -> tuple[FunctionView, ...]:
        """Every function of every module, in surface order."""
        return tuple(function for module in self.modules for function in module.functions)

    @property
    def header_names(self) -> tuple[str, ...]:
        """File names of the adapter headers, in surface order."""
        return tuple(module.header_name for module in self.modules)
