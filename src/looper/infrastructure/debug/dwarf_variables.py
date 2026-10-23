"""Reading one variable entry at a time out of the debug information.

The questions a reader of DWARF keeps asking: is this entry a global,
where does it sit, what is its type, which unit was it compiled in,
and is that unit the firmware's or looper's own. None of them is about
variables as a whole, which is why they are here rather than in the
reader that strings them together.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

from elftools.dwarf.die import DIE

from looper.domain.model.firmware import FirmwareVariable, VariableOrigin
from looper.infrastructure.runtime_location import runtime_sources

DW_OP_ADDR = 0x03

VARIABLE_TAG = "DW_TAG_variable"
NAME_ATTRIBUTE = "DW_AT_name"
COMPILATION_DIRECTORY_ATTRIBUTE = "DW_AT_comp_dir"
TYPE_ATTRIBUTE = "DW_AT_type"
LOCATION_ATTRIBUTE = "DW_AT_location"
DECLARATION_ATTRIBUTE = "DW_AT_declaration"

# A definition does not always carry its own name. A compiler that has
# already described a variable where it was declared writes the definition as
# an entry that says only where it ended up, and points back at the
# declaration for everything else. Following that link is what makes those
# variables appear at all.
SPECIFICATION_ATTRIBUTES = ("DW_AT_specification", "DW_AT_abstract_origin")


def global_variables(root: DIE) -> Iterator[DIE]:
    """Yield the variable entries declared at the file scope of one unit.

    Children of the compilation unit are exactly the file scope declarations.
    Anything inside a function is a child of that function instead, so walking
    one level is what makes this globals only.
    """
    for die in root.iter_children():
        if die.tag == VARIABLE_TAG:
            yield die


def static_address(die: DIE, address_size: int) -> int | None:
    """Read the fixed address of a variable, if it has one.

    An entry whose location is anything but a plain address -- a stack offset,
    a register, a location list -- describes something that is not at one
    place for the life of the process, so there is nothing to watch.
    """
    location = die.attributes.get(LOCATION_ATTRIBUTE)
    if location is None:
        return None
    expression = location.value
    if not isinstance(expression, (bytes, list)):
        return None
    if len(expression) != address_size + 1 or expression[0] != DW_OP_ADDR:
        return None
    return int.from_bytes(bytes(expression[1:]), "little")


def attributed_to(
    variable: FirmwareVariable, source: str | None, origin: VariableOrigin
) -> FirmwareVariable:
    """Record which compilation unit described the variable, and whose it is.

    Replacing fields rather than rebuilding the whole variable: a rebuild
    silently drops whatever the constructor call forgot, and it did.
    """
    if source is None:
        return replace(variable, origin=origin)
    return replace(variable, declared_in=source, origin=origin)


def compiled_in(root: DIE) -> str | None:
    """The directory a compilation unit was compiled from, if it says."""
    directory = root.attributes.get(COMPILATION_DIRECTORY_ATTRIBUTE)
    if directory is None:
        return None
    value = directory.value
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value)


def within_tree(compiled_in: str, tree: Path) -> bool:
    """Whether a compilation directory belongs to the build that was made here.

    The C runtime the linker pulls in to make a process at all was compiled
    years earlier on somebody else's machine, and says so: its units carry
    a compilation directory in a build tree that has nothing to do with
    this one. Everything this build compiled was compiled either in the
    directory the executable landed in, below it, or above it -- one
    compiler invocation from the project root, one build directory, or one
    sub directory per target, depending on who did the building.

    An unrecognisable directory therefore means a prebuilt library. Being
    wrong about it only hides something a tick box brings back, which is
    the right way round for a guess.
    """
    try:
        directory = Path(compiled_in).resolve()
    except (OSError, ValueError):
        return True
    return directory == tree or directory in tree.parents or tree in directory.parents


def simulation_units() -> frozenset[str]:
    """Names of the translation units the simulation brings with it.

    Taken from the package rather than guessed from a prefix, and compared
    by file name rather than by path: the same runtime is compiled from one
    place by looper-cli and from another by a CMake project that fetched
    it, and a path would only recognise one of them.

    The generated adapters are not in the set. They declare one table of
    function pointers between them, and a pointer is not offered anyway.
    """
    return frozenset(path.name for path in runtime_sources())


def described_by(die: DIE) -> DIE | None:
    """Follow a definition to the declaration that describes it, if any."""
    for attribute in SPECIFICATION_ATTRIBUTES:
        if attribute in die.attributes:
            return die.get_DIE_from_attribute(attribute)
    return None


def type_of(die: DIE | None) -> DIE | None:
    """Follow a variable entry to its type, if it names one."""
    if die is None or TYPE_ATTRIBUTE not in die.attributes:
        return None
    return die.get_DIE_from_attribute(TYPE_ATTRIBUTE)


def name_of(die: DIE | None) -> str | None:
    """Read the name of an entry, if it carries one."""
    if die is None:
        return None
    name = die.attributes.get(NAME_ATTRIBUTE)
    if name is None:
        return None
    value = name.value
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value)
