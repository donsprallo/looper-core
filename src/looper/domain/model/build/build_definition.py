"""Description of how one firmware project builds its simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from looper.domain.model.c_api.validation import ensure_non_empty

DEFAULT_LANGUAGE_STANDARD = "c11"
DEFAULT_WARNING_FLAGS = ("-Wall", "-Wextra")
JOURNAL_DEFINITION = "LOOPER_JOURNAL"


@dataclass(frozen=True)
class SimulationBuildDefinition:
    """Everything needed to turn a firmware project into a simulation.

    Paths are resolved against the directory of the definition file before the
    value object is constructed, so every path here is absolute.

    Attributes:
        name: Name of the simulation, used for the default executable name.
        header_directory: Adapter headers the simulation is generated from.
        generated_directory: Where the generated sources are written.
        executable: Path of the executable to produce.
        source_directories: Directories holding firmware and device model code.
        excluded_sources: Translation units to leave out of the build.
        include_directories: Include directories passed to the compiler.
        definitions: Preprocessor definitions passed to the compiler.
        contract_path: Contract definition, or ``None`` to build without one.
        parse_include_directories: Extra include directories used only while
            reading the adapter headers.
        parse_definitions: Extra definitions used only while reading them.
        compiler: Compiler to invoke, or ``None`` to detect one.
        language_standard: C standard the simulation is compiled against.
        warning_flags: Warning flags passed to the compiler.
        record_calls: Whether generated adapters record their calls.
        components: Components that ship with looper and that this board
            carries, named without their ``looper_`` prefix.
        project_root: Directory the definition itself lives in, which is
            what every relative path in it was resolved against. It is
            also what separates the project's own sources -- the device
            model standing in for a board -- from the firmware it points
            at somewhere else.
        track_allocations: Whether to put looper's wrappers in front of
            the allocator, so that a client can see what the firmware
            asks for and what it never gives back. A link time switch:
            it changes no code, only which malloc the calls reach.
        memory_budget: Bytes of writable static memory the project
            allows itself, or zero for no limit. Checked against the
            simulation's own bytes, which is a guide rather than a
            measurement of the target: a pointer is wider here.
        profile: Whether to weave the firmware and the device model with
            instrumentation, so that a client can see where the whole
            simulation spends its time rather than only what the adapter
            boundary costs. It makes a different program: about forty
            nanoseconds per call, and no inlining of what is woven.
    """

    name: str
    header_directory: Path
    generated_directory: Path
    executable: Path
    source_directories: tuple[Path, ...] = field(default_factory=tuple)
    excluded_sources: tuple[Path, ...] = field(default_factory=tuple)
    include_directories: tuple[Path, ...] = field(default_factory=tuple)
    definitions: tuple[str, ...] = field(default_factory=tuple)
    contract_path: Path | None = None
    parse_include_directories: tuple[Path, ...] = field(default_factory=tuple)
    parse_definitions: tuple[str, ...] = field(default_factory=tuple)
    compiler: str | None = None
    language_standard: str = DEFAULT_LANGUAGE_STANDARD
    warning_flags: tuple[str, ...] = DEFAULT_WARNING_FLAGS
    record_calls: bool = True
    components: tuple[str, ...] = field(default_factory=tuple)
    project_root: Path | None = None
    profile: bool = False
    track_allocations: bool = False
    memory_budget: int = 0

    def __post_init__(self) -> None:
        ensure_non_empty(self.name, "A simulation name")
        ensure_non_empty(self.language_standard, "A language standard")
        if self.memory_budget < 0:
            raise ValueError("A memory budget is not negative")

    @property
    def all_definitions(self) -> tuple[str, ...]:
        """Preprocessor definitions including the call recording switch."""
        if not self.record_calls:
            return self.definitions
        return (*self.definitions, JOURNAL_DEFINITION)

    def includes_source(self, source: Path) -> bool:
        """Report whether a source file takes part in the build."""
        return source.resolve() not in {path.resolve() for path in self.excluded_sources}

    @property
    def standard_flag(self) -> str:
        """The flag selecting the C standard."""
        return f"-std={self.language_standard}"
