"""What the three memory reports say, and what they refuse to say.

Every one of them is a host measurement standing in for a target, so
the thing to defend is the wording of each claim: which numbers are
the firmware's own, which are this machine's, and which questions are
not answered at all in a build that was not asked to answer them.
"""

from __future__ import annotations

from pathlib import PurePath

import pytest

from looper.domain.model.firmware import FunctionSymbol
from looper.domain.model.memory import (
    AllocationSite,
    HeapUsage,
    StackFrame,
    StackUsage,
    StaticMemoryReport,
    StaticObject,
    kibibytes,
)
from looper.domain.model.sources import FunctionOrigin
from looper.domain.services import SymbolIndex

APP = PurePath("C:/fw/app/Src/app.c")
RUNTIME = PurePath("C:/looper/runtime/src/looper_clock.c")


def an_object(
    name: str,
    bytes_used: int,
    origin: FunctionOrigin = FunctionOrigin.FIRMWARE,
    is_constant: bool = False,
    source: PurePath = APP,
) -> StaticObject:
    """One statically allocated object."""
    return StaticObject(
        name=name,
        origin=origin,
        source=source,
        bytes_used=bytes_used,
        is_constant=is_constant,
    )


def test_a_read_only_table_is_not_part_of_what_can_be_written() -> None:
    """On a target it costs flash, which is not the budget anyone means."""
    report = StaticMemoryReport(
        objects=(an_object("table", 4096, is_constant=True), an_object("state", 100))
    )

    assert report.total_bytes == 4196
    assert report.writable_bytes == 100


def test_the_firmware_is_counted_apart_from_the_machinery() -> None:
    report = StaticMemoryReport(
        objects=(
            an_object("g_state", 300),
            an_object("queues", 500, FunctionOrigin.RUNTIME, source=RUNTIME),
        )
    )

    assert report.writable_bytes == 800
    assert report.firmware_bytes == 300


def test_a_budget_is_checked_against_what_can_be_written() -> None:
    objects = (an_object("table", 4096, is_constant=True), an_object("state", 100))

    assert StaticMemoryReport(objects=objects, budget_bytes=200).is_within_budget
    assert not StaticMemoryReport(objects=objects, budget_bytes=50).is_within_budget


def test_no_budget_is_not_a_budget_of_nothing() -> None:
    report = StaticMemoryReport(objects=(an_object("state", 10_000),))

    assert report.is_within_budget


def test_the_biggest_objects_are_where_a_budget_goes() -> None:
    report = StaticMemoryReport(objects=(an_object("small", 10), an_object("huge", 30_000)))

    assert [one.name for one in report.biggest(1)] == ["huge"]


def test_a_stack_that_was_never_measured_says_so() -> None:
    assert StackUsage().is_empty


def test_the_deepest_path_adds_up_to_less_than_the_deepest_point() -> None:
    """A frame holds more than its locals, and a path may be cut short."""
    usage = StackUsage(
        deepest_bytes=1000,
        deepest_depth=3,
        path=(
            StackFrame("app_run", FunctionOrigin.FIRMWARE, APP, 100),
            StackFrame("app_step", FunctionOrigin.FIRMWARE, APP, 200),
        ),
    )

    assert usage.path_bytes == 300


def test_the_functions_that_put_the_most_on_the_stack_come_first() -> None:
    usage = StackUsage(
        frames=(
            StackFrame("small", FunctionOrigin.FIRMWARE, APP, 16),
            StackFrame("buffered", FunctionOrigin.FIRMWARE, APP, 2048),
        )
    )

    assert [one.function for one in usage.largest_frames(1)] == ["buffered"]


def test_a_build_that_is_not_watching_does_not_claim_nothing_was_allocated() -> None:
    """Not looking and seeing nothing are different answers."""
    assert not HeapUsage(allocations=0, is_watched=False).never_allocated
    assert HeapUsage(allocations=0, is_watched=True).never_allocated


def test_what_a_library_holds_is_kept_apart_from_the_firmware() -> None:
    usage = HeapUsage(
        is_watched=True,
        outstanding=(
            AllocationSite("app_start", FunctionOrigin.FIRMWARE, APP, 1, 300),
            AllocationSite("printf", FunctionOrigin.LIBRARY, None, 3, 78),
        ),
    )

    assert usage.outstanding_blocks == 4
    assert usage.firmware_outstanding_bytes == 300
    assert [one.function for one in usage.firmware_outstanding] == ["app_start"]


def test_a_size_is_written_the_way_a_person_reads_it() -> None:
    assert kibibytes(512) == "512 B"
    assert kibibytes(2048) == "2.0 KiB"


def test_an_address_inside_a_function_finds_that_function() -> None:
    """An allocation reports a return address, not an entry address."""
    index = SymbolIndex.of(
        (
            FunctionSymbol("first", 0x1000, APP, size_bytes=0x100),
            FunctionSymbol("second", 0x2000, APP, size_bytes=0x100),
        )
    )

    assert index.containing(0x2040) is not None
    assert index.containing(0x2040).name == "second"  # type: ignore[union-attr]
    assert index.at(0x2000) is not None
    assert index.at(0x2040) is None


def test_an_address_outside_every_function_is_given_no_name() -> None:
    """A wrong name in a leak report is worse than a hexadecimal one."""
    index = SymbolIndex.of((FunctionSymbol("only", 0x1000, APP, size_bytes=0x10),))

    assert index.containing(0x900) is None
    assert index.containing(0x5000) is None


def test_a_function_of_unknown_extent_claims_only_its_own_address() -> None:
    index = SymbolIndex.of((FunctionSymbol("only", 0x1000, APP),))

    assert index.containing(0x1000) is not None
    assert index.containing(0x1001) is None


def test_a_negative_amount_is_refused_rather_than_shown() -> None:
    with pytest.raises(ValueError, match="negative"):
        StaticMemoryReport(budget_bytes=-1)
    with pytest.raises(ValueError, match="does not go negative"):
        StackUsage(deepest_bytes=-1)
