"""Working out which part of a simulation each directory holds.

Nobody writes this down, so it is inferred, and the inference has to be
right in the two arrangements that occur: a firmware checked out beside
the project that simulates it, and a small example that is both.
"""

from __future__ import annotations

from pathlib import Path, PurePath

from looper.domain.model.build import SimulationBuildDefinition
from looper.domain.model.sources import FunctionOrigin
from looper.infrastructure.profile_layout import default_source_layout, layout_of
from looper.infrastructure.runtime_location import runtime_root

PROJECT = Path("C:/work/simulations/demo")
FIRMWARE = Path("C:/work/demo-firmware")


def a_definition(*sources: Path, root: Path | None = PROJECT) -> SimulationBuildDefinition:
    """A build definition naming the given source directories."""
    return SimulationBuildDefinition(
        name="demo",
        header_directory=FIRMWARE / "Inc",
        generated_directory=PROJECT / "build" / "generated",
        executable=PROJECT / "build" / "demo.exe",
        source_directories=sources,
        project_root=root,
    )


def test_the_projects_own_source_is_the_device_model() -> None:
    layout = layout_of(a_definition(PROJECT / "src", FIRMWARE / "app" / "Src"))

    assert layout.origin_of(PurePath(PROJECT / "src" / "board.c")) is FunctionOrigin.DEVICE_MODEL
    assert layout.origin_of(PurePath(FIRMWARE / "app" / "Src" / "app.c")) is FunctionOrigin.FIRMWARE


def test_the_generated_adapter_is_not_the_device_model_it_sits_beside() -> None:
    layout = layout_of(a_definition(PROJECT / "src", FIRMWARE / "app"))

    generated = PurePath(PROJECT / "build" / "generated" / "sil_adapter_spi.c")
    assert layout.origin_of(generated) is FunctionOrigin.ADAPTER


def test_a_project_pointing_at_nothing_outside_itself_is_all_firmware() -> None:
    """An example that is its own firmware has nothing to separate."""
    layout = layout_of(a_definition(PROJECT / "src"))

    assert layout.origin_of(PurePath(PROJECT / "src" / "app.c")) is FunctionOrigin.FIRMWARE


def test_the_runtime_is_recognised_wherever_the_project_is() -> None:
    layout = layout_of(a_definition(PROJECT / "src"))

    inside_runtime = PurePath(runtime_root() / "src" / "looper_clock.c")
    assert layout.origin_of(inside_runtime) is FunctionOrigin.RUNTIME


def test_a_definition_without_a_root_falls_back_to_what_is_certain() -> None:
    layout = layout_of(a_definition(PROJECT / "src", root=None))

    assert layout.device_model == ()
    assert layout.origin_of(PurePath(runtime_root() / "src" / "x.c")) is FunctionOrigin.RUNTIME


def test_a_client_without_a_definition_still_knows_its_own_machinery() -> None:
    layout = default_source_layout()

    assert layout.origin_of(PurePath(runtime_root() / "src" / "x.c")) is FunctionOrigin.RUNTIME
    assert layout.origin_of(PurePath("C:/anywhere/app.c")) is FunctionOrigin.FIRMWARE
    assert layout.origin_of(None) is FunctionOrigin.LIBRARY
