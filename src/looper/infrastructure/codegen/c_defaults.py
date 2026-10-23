"""Default values returned by a generated adapter when no hook is installed."""

from __future__ import annotations

from looper.domain.model.c_api import CType, CTypeKind

BOOLEAN_DEFAULT = "false"
INTEGER_DEFAULT = "0"
FLOATING_DEFAULT = "0.0"
POINTER_DEFAULT = "NULL"

SIMPLE_DEFAULTS = {
    CTypeKind.BOOLEAN: BOOLEAN_DEFAULT,
    CTypeKind.INTEGER: INTEGER_DEFAULT,
    CTypeKind.FLOATING: FLOATING_DEFAULT,
    CTypeKind.POINTER: POINTER_DEFAULT,
    CTypeKind.FUNCTION_POINTER: POINTER_DEFAULT,
}


def default_return_expression(return_type: CType) -> str | None:
    """Build the expression a generated function returns without a hook.

    Every default is the zero value of its type. A boolean returns ``false``
    rather than ``true``, so an unimplemented adapter reports that it did
    nothing instead of silently claiming success.

    Returns:
        The expression, or ``None`` when the function returns ``void``.
    """
    if return_type.kind is CTypeKind.VOID:
        return None
    simple = SIMPLE_DEFAULTS.get(return_type.kind)
    if simple is not None:
        return simple
    if return_type.kind is CTypeKind.ENUMERATION:
        return f"({return_type.spelling})0"
    return f"({return_type.spelling}){{0}}"


def zero_value_expression(value_type: CType) -> str:
    """Build a compound literal that zeroes one value of the given type."""
    return f"({value_type.spelling}){{0}}"
