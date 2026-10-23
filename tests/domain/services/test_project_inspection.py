"""What an inspection says about a project before it is run.

The value of these checks is entirely in what they do not say. A warning
about every call would be read once and then switched off, so each test
here pairs the case that must be reported with the case next to it that
must stay quiet.
"""

from __future__ import annotations

from pathlib import Path

from looper.domain.model.analysis import (
    AnalysisReport,
    ArgumentStorage,
    CallArgument,
    CallSite,
    FindingKind,
    FirmwareUsage,
    SourceLocation,
)
from looper.domain.model.c_api import (
    AdapterModule,
    AdapterSurface,
    CExternData,
    CFunction,
    CParameter,
    CType,
    CTypeKind,
)
from looper.domain.model.contract import (
    AdapterContract,
    BufferLifetime,
    BusRole,
    BusRoleKind,
    FunctionContract,
    ParameterContract,
    ParameterRole,
    WriteMoment,
)
from looper.domain.services import inspect_project

BOOLEAN = CType(spelling="bool", kind=CTypeKind.BOOLEAN)
VOID = CType(spelling="void", kind=CTypeKind.VOID)
BYTE = CType(spelling="uint8_t", kind=CTypeKind.INTEGER)
BYTE_POINTER = CType(spelling="uint8_t *", kind=CTypeKind.POINTER, pointee=BYTE)
VOID_POINTER = CType(spelling="void *", kind=CTypeKind.POINTER, pointee=VOID)
TABLE = CType(spelling="embd_gpio_interface_t", kind=CTypeKind.RECORD)

SPI_TRANSFER = CFunction(
    name="adapter_spi_dma_transfer",
    return_type=BOOLEAN,
    parameters=(
        CParameter("context", VOID_POINTER),
        CParameter("rx_data", BYTE_POINTER),
    ),
)
GPIO_SET = CFunction(
    name="adapter_mcu_gpio_set",
    return_type=BOOLEAN,
    parameters=(CParameter("pin", BYTE),),
)


def _surface(*functions: CFunction, data: tuple[CExternData, ...] = ()) -> AdapterSurface:
    """One module holding the given declarations."""
    module = AdapterModule(
        name="spi",
        header_path=Path("Inc/adapter_spi.h"),
        functions=functions,
        extern_data=data,
    )
    return AdapterSurface(modules=(module,))


def _retaining_contract() -> AdapterContract:
    """A contract saying the transfer keeps the buffer it is handed."""
    return AdapterContract(
        functions=(
            FunctionContract(
                function_name="adapter_spi_dma_transfer",
                parameters=(
                    ParameterContract(
                        parameter_name="rx_data",
                        role=ParameterRole.OUTPUT,
                        lifetime=BufferLifetime.BORROWED,
                        written_at=WriteMoment.ON_CALLBACK,
                    ),
                ),
            ),
        )
    )


def _call(storage: ArgumentStorage, spelling: str = "buffer") -> CallSite:
    """One call passing something for the retained buffer."""
    return CallSite(
        function="adapter_spi_dma_transfer",
        location=SourceLocation(path=Path("app/Src/adc.c"), line=88),
        arguments=(
            CallArgument("context", "self", ArgumentStorage.UNKNOWN),
            CallArgument("rx_data", spelling, storage),
        ),
        caller="adc_read",
    )


REACHED = frozenset({"adapter_spi_dma_transfer"})


def _usage(
    sites: tuple[CallSite, ...] = (),
    reached_functions: frozenset[str] = REACHED,
    answered_functions: frozenset[str] = REACHED,
    initialised_data: frozenset[str] = frozenset(),
    units_read: int = 10,
    units_unreadable: int = 0,
) -> FirmwareUsage:
    """Usage with everything reached and answered unless a test says otherwise."""
    return FirmwareUsage(
        call_sites=sites,
        reached_functions=reached_functions,
        answered_functions=answered_functions,
        initialised_data=initialised_data,
        units_read=units_read,
        units_unreadable=units_unreadable,
    )


def _kinds(report: AnalysisReport) -> list[FindingKind]:
    """The kinds a report found, in order."""
    return [finding.kind for finding in report.findings]


def test_a_table_the_build_leaves_empty_is_reported() -> None:
    surface = _surface(GPIO_SET, data=(CExternData("mcu_gpio_interface", TABLE),))

    report = inspect_project(surface, AdapterContract(), _usage())

    assert report.findings[0].kind is FindingKind.EXPORTED_DATA_WITHOUT_INITIALISER
    assert "LOOPER_INIT_mcu_gpio_interface" in report.findings[0].detail


def test_a_table_the_build_fills_is_not_reported() -> None:
    surface = _surface(GPIO_SET, data=(CExternData("mcu_gpio_interface", TABLE),))

    report = inspect_project(
        surface,
        AdapterContract(),
        _usage(initialised_data=frozenset({"mcu_gpio_interface"})),
    )

    assert FindingKind.EXPORTED_DATA_WITHOUT_INITIALISER not in _kinds(report)


def test_a_retained_pointer_to_a_local_is_reported_where_it_is_passed() -> None:
    report = inspect_project(
        _surface(SPI_TRANSFER),
        _retaining_contract(),
        _usage(sites=(_call(ArgumentStorage.AUTOMATIC, "frame"),)),
    )

    finding = report.findings[0]
    assert finding.kind is FindingKind.BORROWED_POINTER_TO_LOCAL
    assert finding.location is not None
    assert finding.location.text == "adc.c:88"
    assert "frame" in finding.detail
    assert "adc_read" in finding.detail


def test_a_retained_pointer_to_a_static_buffer_is_not_reported() -> None:
    report = inspect_project(
        _surface(SPI_TRANSFER),
        _retaining_contract(),
        _usage(sites=(_call(ArgumentStorage.STATIC),)),
    )

    assert report.is_clean


def test_a_pointer_the_adapter_copies_may_be_a_local() -> None:
    """Only a pointer the adapter keeps outlives the caller's frame."""
    contract = AdapterContract(
        functions=(
            FunctionContract(
                function_name="adapter_spi_dma_transfer",
                parameters=(
                    ParameterContract(
                        parameter_name="rx_data",
                        role=ParameterRole.OUTPUT,
                        lifetime=BufferLifetime.COPIED,
                    ),
                ),
            ),
        )
    )

    report = inspect_project(
        _surface(SPI_TRANSFER), contract, _usage(sites=(_call(ArgumentStorage.AUTOMATIC),))
    )

    assert report.is_clean


def test_a_bus_function_nothing_carries_out_is_reported() -> None:
    report = inspect_project(
        _surface(SPI_TRANSFER),
        AdapterContract(),
        _usage(answered_functions=frozenset()),
    )

    assert _kinds(report) == [FindingKind.BUS_FUNCTION_WITHOUT_ROLE]


def test_a_bus_function_with_a_role_is_not_reported() -> None:
    contract = AdapterContract(
        roles={
            "adapter_spi_dma_transfer": BusRole(
                kind=BusRoleKind.SPI_TRANSFER,
                context="context",
                received="rx_data",
                transmitted="rx_data",
                length="length",
            )
        }
    )

    report = inspect_project(
        _surface(SPI_TRANSFER), contract, _usage(answered_functions=frozenset())
    )

    assert report.is_clean


def test_a_bus_function_a_device_model_hooks_is_not_reported() -> None:
    """A hand written model is as good an answer as a generated one."""
    report = inspect_project(_surface(SPI_TRANSFER), AdapterContract(), _usage())

    assert report.is_clean


def test_a_function_no_source_names_is_listed_without_being_a_defect() -> None:
    report = inspect_project(
        _surface(SPI_TRANSFER),
        AdapterContract(),
        _usage(reached_functions=frozenset(), answered_functions=frozenset()),
    )

    assert _kinds(report) == [FindingKind.NEVER_CALLED]
    assert report.defects == ()
    assert report.is_clean


def test_a_report_says_how_much_of_the_project_it_could_read() -> None:
    report = inspect_project(
        _surface(SPI_TRANSFER), AdapterContract(), _usage(units_read=8, units_unreadable=2)
    )

    assert report.coverage_note == "read 8 of 10 translation units"
    assert not report.is_clean
