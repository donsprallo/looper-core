"""Reading one call's arguments well enough to judge them.

A contract speaks about parameters by name and says things about them
that only hold for certain arguments: a pointer the adapter keeps is
fine when it points at a static buffer and a fault when it points at a
local. Both of those are questions about the argument as written, so
this is where an expression is traced back to the declaration underneath
it.
"""

from __future__ import annotations

from clang.cindex import Cursor, CursorKind, StorageClass

from looper.domain.model.analysis import ArgumentStorage, CallArgument

#: Expressions that stand between a call and the declaration it names.
#: Stripping them is what turns a cast of an address back into a variable.
TRANSPARENT_KINDS = frozenset(
    {
        CursorKind.UNEXPOSED_EXPR,
        CursorKind.PAREN_EXPR,
        CursorKind.CSTYLE_CAST_EXPR,
        CursorKind.UNARY_OPERATOR,
        CursorKind.ARRAY_SUBSCRIPT_EXPR,
    }
)

MAXIMUM_DEPTH = 8


def arguments_of(cursor: Cursor, called: Cursor) -> tuple[CallArgument, ...]:
    """Pair what was passed with the parameter it was passed for."""
    names = _parameter_names(called)
    return tuple(
        CallArgument(
            parameter_name=names[index] if index < len(names) else f"argument {index}",
            spelling=_spelling_of(argument),
            storage=_storage_of(argument),
        )
        for index, argument in enumerate(cursor.get_arguments())
    )


def _parameter_names(called: Cursor) -> list[str]:
    """What the adapter calls each parameter, as far as it says.

    The declaration a call refers to may be a prototype without names;
    the canonical declaration usually carries them.
    """
    for declaration in (called, called.canonical):
        names = [child.spelling for child in declaration.get_arguments()]
        if any(names):
            return names
    return []


def _spelling_of(argument: Cursor) -> str:
    """What the caller wrote, as far as the tokens say."""
    tokens = [token.spelling for token in argument.get_tokens()]
    return "".join(tokens) if tokens else argument.spelling


def _storage_of(argument: Cursor) -> ArgumentStorage:
    """Where what an argument points at lives."""
    declaration = _declaration_behind(argument)
    if declaration is None:
        return ArgumentStorage.UNKNOWN
    if declaration.kind is not CursorKind.VAR_DECL:
        return ArgumentStorage.UNKNOWN
    if declaration.storage_class in (StorageClass.STATIC, StorageClass.EXTERN):
        return ArgumentStorage.STATIC
    parent = declaration.semantic_parent
    if (parent is not None) and (parent.kind is CursorKind.FUNCTION_DECL):
        return ArgumentStorage.AUTOMATIC
    return ArgumentStorage.STATIC


def _declaration_behind(argument: Cursor) -> Cursor | None:
    """Follow casts, parentheses and address-of to the variable underneath."""
    cursor: Cursor | None = argument
    for _ in range(MAXIMUM_DEPTH):
        if cursor is None:
            return None
        if cursor.kind is CursorKind.DECL_REF_EXPR:
            return cursor.referenced
        if cursor.kind not in TRANSPARENT_KINDS:
            return None
        children = list(cursor.get_children())
        cursor = children[0] if children else None
    return None
