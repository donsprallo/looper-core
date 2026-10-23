"""Finding every place the firmware reaches the adapter.

The same front end that reads the adapter headers can read the firmware
that calls them, with the include directories and definitions the build
already writes down. What comes out is one record per call: which adapter
function, where, and for each argument enough to judge it against the
contract.

Three things are counted, not one. Firmware rarely calls an adapter by
name everywhere: it fills a table of function pointers once and calls
through the table forever, so a mention counts as a reach. And a device
model answers a call by storing its own function in the hook table, so a
hook field that is written to counts as an answer.

A unit the front end cannot read is counted rather than hidden. A clean
report over half the sources is not a clean report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from clang.cindex import Cursor, CursorKind, Diagnostic, Index

from looper.domain.model.analysis import CallSite, SourceLocation
from looper.infrastructure.analysis.call_arguments import arguments_of
from looper.infrastructure.parsing.clang_library import create_index
from looper.infrastructure.parsing.parse_options import ParseOptions

BLOCKING_SEVERITIES = frozenset({Diagnostic.Error, Diagnostic.Fatal})

NAMING_KINDS = frozenset({CursorKind.CALL_EXPR, CursorKind.DECL_REF_EXPR})

#: How the generator spells the type of a hook table field.
HOOK_TYPE_SUFFIX = "_hook_t"


@dataclass
class _UnitFindings:
    """What one translation unit had to say, while it is being read."""

    sites: list[CallSite] = field(default_factory=list)
    references: set[str] = field(default_factory=set)
    hooks: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class FirmwareScan:
    """Every call the firmware makes into the adapter, and what was read.

    Attributes:
        call_sites: One record per call, in the order they were found.
        referenced_functions: Adapter functions the project names at all,
            whether it calls them or stores them in a table of pointers.
        hooked_functions: Adapter functions whose hook field the device
            model touches, which is how it answers a call.
        units_read: Translation units the front end could read.
        units_unreadable: Translation units it could not.
    """

    call_sites: tuple[CallSite, ...] = field(default_factory=tuple)
    referenced_functions: frozenset[str] = frozenset()
    hooked_functions: frozenset[str] = frozenset()
    units_read: int = 0
    units_unreadable: int = 0

    def calls_to(self, function: str) -> tuple[CallSite, ...]:
        """Every place one adapter function is called."""
        return tuple(site for site in self.call_sites if site.function == function)

    @property
    def called_functions(self) -> frozenset[str]:
        """Names of the adapter functions the project calls by name."""
        return frozenset(site.function for site in self.call_sites)

    @property
    def reached_functions(self) -> frozenset[str]:
        """Names the project reaches at all, by call, pointer or hook."""
        return self.referenced_functions | self.hooked_functions


class FirmwareScanner:
    """Reads a project's own sources and records what they call."""

    def __init__(self, options: ParseOptions) -> None:
        self._options = options
        self._index: Index | None = None

    def scan(self, sources: tuple[Path, ...], wanted: frozenset[str]) -> FirmwareScan:
        """Find every call to, and every mention of, the wanted functions.

        Args:
            sources: Translation units of the project.
            wanted: Adapter function names worth recording.
        """
        total = _UnitFindings()
        read = unreadable = 0
        for source in sources:
            found = self._scan_unit(source, wanted)
            if found is None:
                unreadable += 1
                continue
            read += 1
            total.sites.extend(found.sites)
            total.references |= found.references
            total.hooks |= found.hooks
        return FirmwareScan(
            call_sites=tuple(total.sites),
            referenced_functions=frozenset(total.references),
            hooked_functions=frozenset(total.hooks),
            units_read=read,
            units_unreadable=unreadable,
        )

    def _scan_unit(self, source: Path, wanted: frozenset[str]) -> _UnitFindings | None:
        """Read one unit, or report that it could not be read."""
        if self._index is None:
            self._index = create_index()
        try:
            unit = self._index.parse(str(source), args=self._options.clang_arguments())
        except Exception:  # noqa: BLE001 - the front end raises bare exceptions
            return None
        if any(one.severity in BLOCKING_SEVERITIES for one in unit.diagnostics):
            return None
        found = _UnitFindings()
        _walk(unit.cursor, wanted, caller="", into=found)
        return found


def _walk(cursor: Cursor, wanted: frozenset[str], caller: str, into: _UnitFindings) -> None:
    """Walk a subtree, collecting the calls and mentions worth recording."""
    inside = cursor.spelling if cursor.kind is CursorKind.FUNCTION_DECL else caller
    _record(cursor, wanted, inside, into)
    for child in cursor.get_children():
        _walk(child, wanted, inside, into)


def _record(cursor: Cursor, wanted: frozenset[str], caller: str, into: _UnitFindings) -> None:
    """Note what one cursor says about the wanted functions, if anything."""
    installed = _installed_hook_at(cursor, wanted)
    if installed is not None:
        into.hooks.add(installed)
        return
    named = _adapter_function_at(cursor, wanted)
    if named is None:
        return
    into.references.add(named.spelling)
    if cursor.kind is not CursorKind.CALL_EXPR:
        return
    site = _call_site(cursor, named, caller)
    if site is not None:
        into.sites.append(site)


def _installed_hook_at(cursor: Cursor, wanted: frozenset[str]) -> str | None:
    """The hook a cursor installs, when it installs one.

    A device model answers a call by writing its own function into the
    hook table. Reading that table is what the generated adapter does on
    every call, so only an assignment counts.
    """
    if cursor.kind is not CursorKind.BINARY_OPERATOR:
        return None
    children = list(cursor.get_children())
    if len(children) != 2:
        return None
    target = children[0]
    if (target.kind is not CursorKind.MEMBER_REF_EXPR) or (target.spelling not in wanted):
        return None
    if not _assigns(cursor, target):
        return None
    return target.spelling if _is_hook_field(target) else None


def _is_hook_field(target: Cursor) -> bool:
    """Whether a member reference names a field of the hook table."""
    member = target.referenced
    if (member is None) or (member.kind is not CursorKind.FIELD_DECL):
        return False
    return bool(member.type.spelling.endswith(HOOK_TYPE_SUFFIX))


def _assigns(cursor: Cursor, left: Cursor) -> bool:
    """Whether a binary operator is an assignment rather than a test."""
    after_left = left.extent.end.offset
    for token in cursor.get_tokens():
        if token.extent.start.offset >= after_left:
            return bool(token.spelling == "=")
    return False


def _adapter_function_at(cursor: Cursor, wanted: frozenset[str]) -> Cursor | None:
    """The adapter function a cursor names, when it names one.

    A call through a structure member names a field rather than a
    function, and a field may well carry the same name as one. Only the
    declaration of a function counts.
    """
    if cursor.kind not in NAMING_KINDS:
        return None
    named = cursor.referenced
    if (named is None) or (named.kind is not CursorKind.FUNCTION_DECL):
        return None
    return named if named.spelling in wanted else None


def _call_site(cursor: Cursor, called: Cursor, caller: str) -> CallSite | None:
    """Describe one call to an adapter function."""
    location = cursor.location
    if (location is None) or (location.file is None):
        return None
    return CallSite(
        function=called.spelling,
        location=SourceLocation(path=Path(str(location.file.name)), line=location.line),
        arguments=arguments_of(cursor, called),
        caller=caller,
    )
