"""Rendering of an inspection as plain text.

Findings are grouped by kind rather than listed one after another,
because what a reader does about them differs by kind: one is a line in
the build definition, one a line in the contract, one a buffer that has
to move out of a function. The list of functions nothing names is kept
to one paragraph at the end; it is long, and it is not a fault.
"""

from __future__ import annotations

from collections.abc import Iterator

from looper.application.dto import AuditView, FindingView, StaticMemoryView

NEWLINE = "\n"
NEVER_CALLED = "never_called"
INDENT = "  "


def render_audit(view: AuditView) -> str:
    """Render everything an inspection found."""
    return NEWLINE.join(_lines(view))


def _lines(view: AuditView) -> Iterator[str]:
    """Produce the report line by line."""
    yield f"Audit: {view.coverage_note}"
    yield ""
    yield from _defect_lines(view)
    yield from _unused_lines(view)
    yield from _memory_lines(view)
    yield _summary(view)


def _memory_lines(view: AuditView) -> Iterator[str]:
    """Produce the paragraph about what the build holds statically."""
    if view.static_memory is None:
        if view.memory_note:
            yield f"Static memory: {view.memory_note}"
            yield ""
        return
    yield f"Static memory: {view.static_memory.summary}"
    yield from _directory_lines(view.static_memory)
    yield from _biggest_lines(view.static_memory)
    yield ""


def _directory_lines(memory: StaticMemoryView) -> Iterator[str]:
    """Produce the per directory breakdown."""
    for directory, size in memory.by_directory:
        yield f"{INDENT}{size:>10}  {_shortened(directory)}"


def _biggest_lines(memory: StaticMemoryView) -> Iterator[str]:
    """Produce the list of the largest objects."""
    if not memory.biggest:
        return
    yield f"{INDENT}largest objects:"
    for one in memory.biggest:
        constant = " (read only)" if one.is_constant else ""
        yield f"{INDENT}{INDENT}{one.size_text:>10}  {one.name}  {one.file_name}{constant}"


def _shortened(directory: str) -> str:
    """A directory with enough of its tail to tell it from its neighbours."""
    parts = directory.replace("/", "\\").split("\\")
    return "\\".join(parts[-3:]) if len(parts) > 3 else directory


def _defect_lines(view: AuditView) -> Iterator[str]:
    """Produce one paragraph per kind of defect."""
    for kind in _kinds_of(view.defects):
        yield f"{kind}:"
        for finding in view.of_kind(kind):
            yield f"{INDENT}{finding.line}"
            yield f"{INDENT}{INDENT}{finding.detail}"
        yield ""


def _unused_lines(view: AuditView) -> Iterator[str]:
    """Produce the paragraph listing what nothing names."""
    unused = view.of_kind(NEVER_CALLED)
    if not unused:
        return
    yield f"{len(unused)} declared functions no source names:"
    yield f"{INDENT}{', '.join(finding.subject for finding in unused)}"
    yield ""


def _summary(view: AuditView) -> str:
    """Say in one line whether anything has to be acted on."""
    if view.has_nothing_to_act_on:
        return "nothing to act on"
    defects = len(view.defects)
    counts = [f"{defects} defect{'s' if defects != 1 else ''}"] if defects else []
    if view.is_over_budget:
        counts.append("over the memory budget")
    return " and ".join(counts) + " to act on"


def _kinds_of(findings: tuple[FindingView, ...]) -> tuple[str, ...]:
    """The kinds present, in the order they first appear."""
    seen: list[str] = []
    for finding in findings:
        if finding.kind not in seen:
            seen.append(finding.kind)
    return tuple(seen)
