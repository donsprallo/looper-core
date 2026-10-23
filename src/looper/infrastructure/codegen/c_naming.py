"""Naming and declarator rules for the generated C code."""

from __future__ import annotations

from looper.domain.model.c_api import CType

HOOK_PREFIX = "looper_"
HOOK_SUFFIX = "_hook_t"
POINTER_MARKER = "*"
FUNCTION_POINTER_MARKER = "(*)"
GENERATED_SOURCE_PREFIX = "sil_"


def hook_type_name(function_name: str) -> str:
    """Name of the hook function pointer type of one adapter function."""
    return f"{HOOK_PREFIX}{function_name}{HOOK_SUFFIX}"


def generated_source_name(header_name: str) -> str:
    """Name of the generated source file implementing one adapter header."""
    return f"{GENERATED_SOURCE_PREFIX}{header_name.removesuffix('.h')}.c"


def declare(type_spelling: str, name: str) -> str:
    """Build a C declarator for a named object of the given type.

    A declarator is not a type followed by a name. A function pointer spells
    as ``void (*)(void *, _Bool)`` and the name belongs *inside* the
    parentheses, so appending it would produce code that does not compile.

    Args:
        type_spelling: Type as libclang spells it.
        name: Name of the declared object.

    Returns:
        The complete declarator, for example ``void (*callback)(void *)``.
    """
    if FUNCTION_POINTER_MARKER in type_spelling:
        return type_spelling.replace(FUNCTION_POINTER_MARKER, f"(*{name})", 1)
    if type_spelling.endswith(POINTER_MARKER):
        return f"{type_spelling}{name}"
    return f"{type_spelling} {name}"


def declare_parameter(parameter_type: CType, name: str) -> str:
    """Build the declarator of one function parameter."""
    return declare(parameter_type.spelling, name)
