"""How an inspection reads on a terminal.

A report that buries the one thing to fix under a list of forty unused
functions does not get read. These tests are about that order, and
about the report saying plainly when there is nothing to do.
"""

from __future__ import annotations

from looper.application.dto import AuditView, FindingView
from looper.presentation.cli.audit_renderer import render_audit


def _defect(kind: str, subject: str, where: str = "") -> FindingView:
    """One finding that has to be acted on."""
    return FindingView(kind=kind, subject=subject, detail="what follows from it", where=where)


def _note(subject: str) -> FindingView:
    """One finding that is only worth knowing."""
    return FindingView(
        kind="never_called", subject=subject, detail="nothing names it", is_a_defect=False
    )


def test_a_clean_project_is_told_so_in_one_line() -> None:
    rendered = render_audit(AuditView(coverage_note="read all 12 translation units"))

    assert "read all 12 translation units" in rendered
    assert rendered.strip().endswith("nothing to act on")


def test_the_defects_come_before_what_is_only_worth_knowing() -> None:
    view = AuditView(
        findings=(_defect("bus_function_without_role", "adapter_spi_transfer"), _note("panic")),
        is_clean=False,
    )

    rendered = render_audit(view)

    assert rendered.index("adapter_spi_transfer") < rendered.index("panic")
    assert rendered.strip().endswith("1 defect to act on")


def test_a_finding_with_a_place_shows_it_beside_the_subject() -> None:
    view = AuditView(
        findings=(_defect("borrowed_pointer_to_local", "transfer(rx)", "adc.c:88"),),
        is_clean=False,
    )

    assert "transfer(rx)  adc.c:88" in render_audit(view)


def test_what_nothing_names_is_one_paragraph_rather_than_one_line_each() -> None:
    view = AuditView(findings=(_note("panic"), _note("adapter_uart_init")))

    rendered = render_audit(view)

    assert "2 declared functions no source names:" in rendered
    assert "panic, adapter_uart_init" in rendered


def test_every_defect_of_one_kind_is_gathered_under_it() -> None:
    view = AuditView(
        findings=(
            _defect("never_called_table", "one"),
            _defect("borrowed_pointer_to_local", "two"),
            _defect("never_called_table", "three"),
        ),
        is_clean=False,
    )

    headings = [line for line in render_audit(view).splitlines() if line.endswith(":")]

    assert headings == ["never_called_table:", "borrowed_pointer_to_local:"]
