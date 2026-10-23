"""Translation of libclang types into the domain type model."""

from __future__ import annotations

from clang.cindex import Type, TypeKind

from looper.domain.model.c_api import CType, CTypeKind

INTEGER_KINDS = frozenset(
    {
        TypeKind.CHAR_U,
        TypeKind.UCHAR,
        TypeKind.CHAR16,
        TypeKind.CHAR32,
        TypeKind.USHORT,
        TypeKind.UINT,
        TypeKind.ULONG,
        TypeKind.ULONGLONG,
        TypeKind.UINT128,
        TypeKind.CHAR_S,
        TypeKind.SCHAR,
        TypeKind.WCHAR,
        TypeKind.SHORT,
        TypeKind.INT,
        TypeKind.LONG,
        TypeKind.LONGLONG,
        TypeKind.INT128,
    }
)

FLOATING_KINDS = frozenset(
    {TypeKind.FLOAT, TypeKind.DOUBLE, TypeKind.LONGDOUBLE, TypeKind.FLOAT128, TypeKind.HALF}
)

ARRAY_KINDS = frozenset(
    {
        TypeKind.CONSTANTARRAY,
        TypeKind.INCOMPLETEARRAY,
        TypeKind.VARIABLEARRAY,
        TypeKind.DEPENDENTSIZEDARRAY,
    }
)

FUNCTION_KINDS = frozenset({TypeKind.FUNCTIONPROTO, TypeKind.FUNCTIONNOPROTO})


def map_type(clang_type: Type) -> CType:
    """Translate a libclang type into its domain representation.

    The spelling is taken from the declared type so that generated code keeps
    the typedef the header author chose. The classification is taken from the
    canonical type, because a typedef such as ``adapter_spi_callback_t`` only
    reveals itself as a function pointer once it is resolved.
    """
    canonical = clang_type.get_canonical()
    kind = classify(canonical)
    return CType(
        spelling=clang_type.spelling,
        kind=kind,
        is_const=clang_type.is_const_qualified(),
        pointee=_map_pointee(canonical, kind),
        element_count=_element_count(canonical, kind),
    )


def classify(canonical: Type) -> CTypeKind:
    """Classify an already canonicalised libclang type."""
    if canonical.kind is TypeKind.POINTER:
        return _classify_pointer(canonical)
    if canonical.kind in ARRAY_KINDS:
        return CTypeKind.ARRAY
    if canonical.kind in INTEGER_KINDS:
        return CTypeKind.INTEGER
    if canonical.kind in FLOATING_KINDS:
        return CTypeKind.FLOATING
    return _SIMPLE_KINDS.get(canonical.kind, CTypeKind.UNKNOWN)


_SIMPLE_KINDS = {
    TypeKind.VOID: CTypeKind.VOID,
    TypeKind.BOOL: CTypeKind.BOOLEAN,
    TypeKind.ENUM: CTypeKind.ENUMERATION,
    TypeKind.RECORD: CTypeKind.RECORD,
}


def _classify_pointer(canonical: Type) -> CTypeKind:
    """Separate plain data pointers from function pointers."""
    if canonical.get_pointee().kind in FUNCTION_KINDS:
        return CTypeKind.FUNCTION_POINTER
    return CTypeKind.POINTER


def _map_pointee(canonical: Type, kind: CTypeKind) -> CType | None:
    """Translate the addressed type of a pointer or array."""
    if kind is CTypeKind.POINTER:
        return map_type(canonical.get_pointee())
    if kind is CTypeKind.ARRAY:
        return map_type(canonical.get_array_element_type())
    return None


def _element_count(canonical: Type, kind: CTypeKind) -> int | None:
    """Read the declared element count of a fixed size array."""
    if kind is not CTypeKind.ARRAY or canonical.kind is not TypeKind.CONSTANTARRAY:
        return None
    return int(canonical.element_count)
