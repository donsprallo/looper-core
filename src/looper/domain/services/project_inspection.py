"""Checking a project against its own declarations before it is run.

Each check here joins two of the three things a project writes down --
the adapter surface, the contract, and the sources that use them -- and
reports where they disagree. None of them runs anything, and none of
them guesses: a check that cannot tell says nothing rather than warning.

The order the findings come out in is the order of the checks, worst
first: a dispatch through a null table crashes, a borrowed local is a
fault waiting for a change in timing, a missing role silently returns
zero, and an unused function is only worth knowing.
"""

from __future__ import annotations

from looper.domain.model.analysis import (
    AnalysisReport,
    ArgumentStorage,
    CallSite,
    Finding,
    FindingKind,
    FirmwareUsage,
)
from looper.domain.model.c_api.adapter_surface import AdapterSurface
from looper.domain.model.c_api.c_function import CFunction
from looper.domain.model.c_api.c_parameter import CParameter
from looper.domain.model.c_api.c_type import CTypeKind
from looper.domain.model.contract.adapter_contract import AdapterContract
from looper.domain.model.contract.bus_role import BusRoleKind
from looper.domain.model.contract.parameter_contract import (
    BufferLifetime,
    ParameterContract,
    WriteMoment,
)

#: How a build names the value it gives an exported symbol.
INITIALISER_PREFIX = "LOOPER_INIT_"

#: Name fragments that say which bus a function belongs to. CAN is not
#: among them: a CAN controller is driven by acceptance filters rather
#: than by a transfer, and the contract deliberately has no role for it.
BUS_TOKENS = frozenset(kind.bus_kind for kind in BusRoleKind)

#: Name fragments of functions that set a bus up rather than use it. An
#: initialiser is handed the buffers it will later work with, so it has
#: the shape of a transfer without being one, and nothing is lost when a
#: simulation leaves it unanswered.
SETUP_TOKENS = frozenset({"init", "deinit"})


def inspect_project(
    surface: AdapterSurface, contract: AdapterContract, usage: FirmwareUsage
) -> AnalysisReport:
    """Report everything the three descriptions disagree about.

    Args:
        surface: Declarations parsed from the adapter headers.
        contract: Hand written semantics for those declarations.
        usage: What the project's own sources do with them.
    """
    findings = [
        *_uninitialised_tables(surface, usage),
        *_borrowed_locals(contract, usage),
        *_bus_functions_without_role(surface, contract, usage),
        *_never_called(surface, usage),
    ]
    return AnalysisReport(
        findings=tuple(findings),
        units_read=usage.units_read,
        units_unreadable=usage.units_unreadable,
    )


def _uninitialised_tables(surface: AdapterSurface, usage: FirmwareUsage) -> list[Finding]:
    """Report every exported table the simulation leaves at all zeroes."""
    return [
        Finding(
            kind=FindingKind.EXPORTED_DATA_WITHOUT_INITIALISER,
            subject=data.name,
            detail=(
                "the generated adapter defines it as all zeroes, so the first "
                "call through it dispatches to address zero; give the build "
                f"{INITIALISER_PREFIX}{data.name}"
            ),
        )
        for data in surface.extern_data
        if data.is_interface_table and data.name not in usage.initialised_data
    ]


def _borrowed_locals(contract: AdapterContract, usage: FirmwareUsage) -> list[Finding]:
    """Report every call handing a retained pointer something local."""
    return [finding for site in usage.call_sites for finding in _borrowed_locals_at(site, contract)]


def _borrowed_locals_at(site: CallSite, contract: AdapterContract) -> list[Finding]:
    """Report the arguments of one call that will not outlive it."""
    if not contract.covers(site.function):
        return []
    retained = [
        parameter
        for parameter in contract.function(site.function).parameters
        if _is_retained(parameter)
    ]
    return [
        _borrowed_local(site, parameter)
        for parameter in retained
        if _passes_a_local(site, parameter)
    ]


def _is_retained(parameter: ParameterContract) -> bool:
    """Whether the adapter still holds this pointer after it returns."""
    return (parameter.lifetime is BufferLifetime.BORROWED) or (
        parameter.written_at is WriteMoment.ON_CALLBACK
    )


def _passes_a_local(site: CallSite, parameter: ParameterContract) -> bool:
    """Whether what was passed for a parameter dies with its caller."""
    argument = site.argument(parameter.parameter_name)
    return (argument is not None) and (argument.storage is ArgumentStorage.AUTOMATIC)


def _borrowed_local(site: CallSite, parameter: ParameterContract) -> Finding:
    """Describe one pointer the adapter outlives."""
    argument = site.argument(parameter.parameter_name)
    passed = argument.spelling if argument is not None else parameter.parameter_name
    inside = f" of {site.caller}" if site.caller else ""
    return Finding(
        kind=FindingKind.BORROWED_POINTER_TO_LOCAL,
        subject=f"{site.function}({parameter.parameter_name})",
        detail=(
            f"the adapter keeps this pointer past the call, and {passed} is "
            f"a local{inside} that stops existing when it returns"
        ),
        location=site.location,
    )


def _bus_functions_without_role(
    surface: AdapterSurface, contract: AdapterContract, usage: FirmwareUsage
) -> list[Finding]:
    """Report every bus function nothing carries out."""
    return [
        Finding(
            kind=FindingKind.BUS_FUNCTION_WITHOUT_ROLE,
            subject=function.name,
            detail=(
                "the firmware uses it, the contract gives it no role and no "
                "device model hooks it, so it returns the zero value and "
                "nothing reaches the bus"
            ),
        )
        for function in surface.functions
        if _is_unanswered_bus_function(function, contract, usage)
    ]


def _is_unanswered_bus_function(
    function: CFunction, contract: AdapterContract, usage: FirmwareUsage
) -> bool:
    """Whether a function moves bytes over a bus and nothing carries it out."""
    if not _looks_like_a_bus_transfer(function):
        return False
    if contract.role(function.name) is not None:
        return False
    return usage.reaches(function.name) and not usage.answers(function.name)


def _looks_like_a_bus_transfer(function: CFunction) -> bool:
    """Whether a declaration has the shape of moving bytes over a bus.

    Named after a bus, not named as a setup step, and carrying bytes.
    The last of the three is what keeps a configuration pointer from
    counting: that is memory the adapter reads, not memory a bus carries.
    """
    segments = set(function.name.split("_"))
    if not (BUS_TOKENS & segments) or (SETUP_TOKENS & segments):
        return False
    return any(_carries_bytes(parameter) for parameter in function.parameters)


def _carries_bytes(parameter: CParameter) -> bool:
    """Whether a parameter points at plain bytes rather than a structure."""
    pointee = parameter.type.pointee
    return (pointee is not None) and (pointee.kind is CTypeKind.INTEGER)


def _never_called(surface: AdapterSurface, usage: FirmwareUsage) -> list[Finding]:
    """Report every declared function no source names."""
    return [
        Finding(
            kind=FindingKind.NEVER_CALLED,
            subject=function.name,
            detail="no source of the project names it, so its hook never fires",
        )
        for function in surface.functions
        if not usage.reaches(function.name)
    ]
