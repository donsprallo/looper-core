"""That the options `build`, `run` and `audit` accept reach what acts on them.

A flag that parses and is then dropped on the floor is the quietest
kind of broken: the command runs, says something plausible, and does
the opposite of what was asked. `--rebuild` was exactly that on
`run` for a while -- accepted by the parser, never passed on -- so
every option of every command is checked here against the thing that
would have had to receive it, rather than against the parser.

Nothing is assembled, compiled, run or written: each handler's
collaborators are replaced by recorders.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from looper.application.dto import AuditView, BuildSimulationReport
from looper.presentation.cli import audit_command, build_command
from looper.presentation.cli.main import build_parser

DEFINITION = "examples/blinky/looper.toml"
REPORT = BuildSimulationReport(
    name="demo",
    executable=Path("build") / "demo",
    compiler="gcc",
    generated_file_count=3,
    function_count=8,
    uncontracted_count=0,
)


def handle(arguments: Sequence[str]) -> None:
    """Run one command line through the handler it selects."""
    parsed = build_parser().parse_args(arguments)
    parsed.handler(parsed)


class StubUseCase:
    """A build that does nothing, and remembers what it was asked."""

    def __init__(self) -> None:
        self.requests: list[object] = []

    def execute(self, request: object) -> BuildSimulationReport:
        self.requests.append(request)
        return REPORT


class RecordingFactory:
    """Stands in for the assembly, and remembers how it was asked."""

    def __init__(self) -> None:
        self.rebuilds: list[bool] = []
        self.use_case = StubUseCase()

    def __call__(
        self, definition_path: Path, progress: object = None, rebuild: bool = False
    ) -> StubUseCase:
        self.rebuilds.append(rebuild)
        return self.use_case

    @property
    def request(self) -> object:
        """What the use case it handed out was executed with."""
        return self.use_case.requests[-1]


class StubRun:
    """A run that reports a clean stop without starting anything."""

    def __init__(self, build: StubUseCase, runner: object) -> None:
        self._build = build

    def execute(self, request: object) -> int:
        self._build.requests.append(request)
        return 0


def _render_nothing(view: object) -> str:
    """A report nobody reads in these tests."""
    return ""


def _write_nothing(definition: object) -> None:
    """No manifest is written beside a build that never happened."""


class _NoDefinitions:
    """A repository nothing asks anything of in these tests."""

    def load(self, definition_path: Path) -> None:
        return None


@pytest.fixture
def factory(monkeypatch: pytest.MonkeyPatch) -> RecordingFactory:
    """Nothing is assembled, built, run or written to disk."""
    recording = RecordingFactory()
    monkeypatch.setattr(build_command, "_build_use_case", recording)
    monkeypatch.setattr(build_command, "RunSimulation", StubRun)
    monkeypatch.setattr(build_command, "SubprocessSimulationRunner", lambda: None)
    monkeypatch.setattr(build_command, "write_cmake_manifest", _write_nothing)
    monkeypatch.setattr(build_command, "TomlBuildDefinitionRepository", _NoDefinitions)
    return recording


def test_building_without_the_flag_builds_what_is_out_of_date(factory: RecordingFactory) -> None:
    handle(["build", DEFINITION])

    assert factory.rebuilds == [False]


def test_building_with_the_flag_rebuilds(factory: RecordingFactory) -> None:
    handle(["build", DEFINITION, "--rebuild"])

    assert factory.rebuilds == [True]


def test_running_without_the_flag_builds_what_is_out_of_date(factory: RecordingFactory) -> None:
    handle(["run", DEFINITION])

    assert factory.rebuilds == [False]


def test_running_with_the_flag_rebuilds(factory: RecordingFactory) -> None:
    """The one that was broken: accepted by the parser, never passed on."""
    handle(["run", DEFINITION, "--rebuild"])

    assert factory.rebuilds == [True]


def test_the_definition_a_build_was_given_is_the_one_it_builds(
    factory: RecordingFactory,
) -> None:
    handle(["build", DEFINITION])

    assert factory.request.definition_path == Path(DEFINITION)  # type: ignore[attr-defined]


def test_an_incomplete_contract_is_accepted_only_when_asked(
    factory: RecordingFactory,
) -> None:
    handle(["build", DEFINITION])
    strict = factory.request

    handle(["build", DEFINITION, "--allow-incomplete-contract"])

    assert not strict.allow_incomplete_contract  # type: ignore[attr-defined]
    assert factory.request.allow_incomplete_contract  # type: ignore[attr-defined]


def test_a_run_accepts_an_incomplete_contract_only_when_asked(
    factory: RecordingFactory,
) -> None:
    handle(["run", DEFINITION])
    strict = factory.request

    handle(["run", DEFINITION, "--allow-incomplete-contract"])

    assert not strict.allow_incomplete_contract  # type: ignore[attr-defined]
    assert factory.request.allow_incomplete_contract  # type: ignore[attr-defined]


def test_the_port_and_the_clock_reach_the_run(factory: RecordingFactory) -> None:
    handle(["run", DEFINITION, "--port", "45771", "--virtual"])

    request = factory.request
    assert request.port == 45771  # type: ignore[attr-defined]
    assert request.virtual_time  # type: ignore[attr-defined]


def test_a_run_told_not_to_build_says_so_in_its_request(factory: RecordingFactory) -> None:
    handle(["run", DEFINITION, "--no-build"])

    assert factory.request.skip_build  # type: ignore[attr-defined]


def test_a_run_builds_unless_told_not_to(factory: RecordingFactory) -> None:
    handle(["run", DEFINITION])

    assert not factory.request.skip_build  # type: ignore[attr-defined]


def test_the_definition_a_run_was_given_is_the_one_it_runs(factory: RecordingFactory) -> None:
    handle(["run", DEFINITION])

    assert factory.request.definition_path == Path(DEFINITION)  # type: ignore[attr-defined]


class RecordingAudit:
    """Stands in for the audit, and remembers what it was asked."""

    requests: list[object] = []

    def __init__(self, **collaborators: object) -> None:
        self.progress = collaborators["progress"]

    def execute(self, request: object) -> AuditView:
        RecordingAudit.requests.append(request)
        return AuditView()


@pytest.fixture
def audits(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    """Nothing is parsed, read or inspected."""
    RecordingAudit.requests = []
    monkeypatch.setattr(audit_command, "AuditProject", RecordingAudit)
    monkeypatch.setattr(audit_command, "render_audit", _render_nothing)
    return RecordingAudit.requests


def test_the_definition_an_audit_was_given_is_the_one_it_inspects(
    audits: list[object],
) -> None:
    handle(["audit", DEFINITION])

    assert audits[-1].definition_path == Path(DEFINITION)  # type: ignore[attr-defined]


@pytest.mark.parametrize("command", [["build"], ["run"], ["audit"]])
def test_being_quiet_leaves_the_error_stream_empty(
    command: list[str],
    factory: RecordingFactory,
    audits: list[object],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Every command takes the flag, and every command has to honour it."""
    handle([*command, DEFINITION])
    assert capsys.readouterr().err

    handle([*command, DEFINITION, "--quiet"])

    assert capsys.readouterr().err == ""
