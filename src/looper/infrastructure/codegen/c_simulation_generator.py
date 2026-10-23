"""Generation of a host simulation from a parsed adapter surface."""

from __future__ import annotations

from pathlib import PurePosixPath

from jinja2 import Environment, PackageLoader, StrictUndefined

from looper import __version__
from looper.domain.model.c_api import AdapterSurface
from looper.domain.model.codegen import ArtifactKind, GeneratedArtifact
from looper.domain.model.contract import AdapterContract
from looper.domain.ports import AdapterSimulationGenerator
from looper.infrastructure.codegen.binding_builder import ADDRESS as BINDING_ADDRESS
from looper.infrastructure.codegen.binding_builder import BUS as BINDING_BUS
from looper.infrastructure.codegen.view_builder import build_surface_view
from looper.infrastructure.codegen.view_model import ModuleView, SurfaceView

TEMPLATE_PACKAGE = "looper.infrastructure.codegen"
TEMPLATE_DIRECTORY = "templates"

HOOKS_HEADER_NAME = "looper_hooks.h"
HOOKS_SOURCE_NAME = "looper_hooks.c"
HOOKS_HEADER_TEMPLATE = "hooks_header.h.jinja"
HOOKS_SOURCE_TEMPLATE = "hooks_source.c.jinja"
MODULE_SOURCE_TEMPLATE = "module_source.c.jinja"


class CSimulationGenerator(AdapterSimulationGenerator):
    """Renders a hook based C simulation of an adapter surface.

    Every adapter function is generated twice over: as a hook signature a test
    can install, and as the exported function the firmware links against. The
    exported function forwards to the hook when one is installed and applies
    the documented default otherwise.
    """

    def __init__(self) -> None:
        self._environment = Environment(
            loader=PackageLoader(TEMPLATE_PACKAGE, TEMPLATE_DIRECTORY),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
            trim_blocks=False,
            lstrip_blocks=False,
            autoescape=False,
        )

    def generate(
        self, surface: AdapterSurface, contract: AdapterContract
    ) -> tuple[GeneratedArtifact, ...]:
        """Render every file the simulation consists of."""
        view = build_surface_view(surface, contract)
        return (
            self._render_hooks_header(view),
            self._render_hooks_source(),
            *(self._render_module(module) for module in view.modules),
        )

    def _render_hooks_header(self, view: SurfaceView) -> GeneratedArtifact:
        """Render the header declaring every hook."""
        return GeneratedArtifact(
            relative_path=PurePosixPath(HOOKS_HEADER_NAME),
            kind=ArtifactKind.C_HEADER,
            content=self._render(HOOKS_HEADER_TEMPLATE, view=view),
        )

    def _render_hooks_source(self) -> GeneratedArtifact:
        """Render the source defining the shared hook table."""
        return GeneratedArtifact(
            relative_path=PurePosixPath(HOOKS_SOURCE_NAME),
            kind=ArtifactKind.C_SOURCE,
            content=self._render(HOOKS_SOURCE_TEMPLATE),
        )

    def _render_module(self, module: ModuleView) -> GeneratedArtifact:
        """Render the simulation of one adapter header."""
        return GeneratedArtifact(
            relative_path=PurePosixPath(module.source_name),
            kind=ArtifactKind.C_SOURCE,
            content=self._render(MODULE_SOURCE_TEMPLATE, module=module),
        )

    def _render(self, template_name: str, **context: object) -> str:
        """Render one template with the tool version always in scope."""
        template = self._environment.get_template(template_name)
        return template.render(
            version=__version__,
            binding_bus=BINDING_BUS,
            binding_address=BINDING_ADDRESS,
            **context,
        )
