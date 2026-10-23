"""That the options `analyze` and `generate` accept reach what acts on them.

Both read headers, so both carry the front end arguments -- an include
directory or a definition that never reaches the parser is a command
that reads the wrong thing and says nothing about it. The same check
as for the project commands, at the seams these two have.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from looper.presentation.cli import analyze_command, generate_command
from looper.presentation.cli.generate_command import _what_to_generate
from looper.presentation.cli.main import build_parser

HEADERS = "examples/blinky/Inc"
OUTPUT = "build/out"
CONTRACT = "examples/blinky/contract.toml"
DEFINITION = "examples/blinky/looper.toml"


def handle(arguments: Sequence[str]) -> None:
    """Run one command line through the handler it selects."""
    parsed = build_parser().parse_args(arguments)
    parsed.handler(parsed)


def planned(arguments: Sequence[str]) -> tuple[object, object, object]:
    """What a generate command line decided to generate, before it ran."""
    return _what_to_generate(build_parser().parse_args(arguments))


def _render_nothing(report: object) -> str:
    """A report nobody reads in these tests."""
    return ""


class RecordingSurfaces:
    """Stands in for the header reader, and keeps how it was configured."""

    options: list[object] = []

    def __init__(self, options: object) -> None:
        RecordingSurfaces.options.append(options)


class RecordingAnalysis:
    """Stands in for the analysis, and keeps what it was asked."""

    requests: list[object] = []

    def __init__(self, **collaborators: object) -> None:
        self.collaborators = collaborators

    def execute(self, request: object) -> object:
        RecordingAnalysis.requests.append(request)
        return object()


@pytest.fixture
def analysis(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    """Nothing is parsed and no report is rendered."""
    RecordingSurfaces.options = []
    RecordingAnalysis.requests = []
    monkeypatch.setattr(analyze_command, "LibclangAdapterSurfaceRepository", RecordingSurfaces)
    monkeypatch.setattr(analyze_command, "AnalyzeAdapterSurface", RecordingAnalysis)
    monkeypatch.setattr(analyze_command, "render_report", _render_nothing)
    return RecordingAnalysis.requests


def test_the_headers_an_analysis_was_given_are_the_ones_it_reads(
    analysis: list[object],
) -> None:
    handle(["analyze", HEADERS])

    assert RecordingAnalysis.requests[-1].header_directory == Path(HEADERS)  # type: ignore[attr-defined]


def test_the_contract_reaches_the_analysis(analysis: list[object]) -> None:
    handle(["analyze", HEADERS, "--contract", CONTRACT])

    assert RecordingAnalysis.requests[-1].contract_path == Path(CONTRACT)  # type: ignore[attr-defined]


def test_without_a_contract_the_analysis_is_told_there_is_none(
    analysis: list[object],
) -> None:
    handle(["analyze", HEADERS])

    assert RecordingAnalysis.requests[-1].contract_path is None  # type: ignore[attr-defined]


def test_include_directories_and_definitions_reach_the_front_end(
    analysis: list[object],
) -> None:
    """Repeatable, and all of them have to arrive."""
    handle(["analyze", HEADERS, "-I", "one", "-I", "two", "-D", "FAST=1", "-D", "HOST"])

    options = RecordingSurfaces.options[-1]
    assert options.include_directories == (Path("one"), Path("two"))  # type: ignore[attr-defined]
    assert options.definitions == ("FAST=1", "HOST")  # type: ignore[attr-defined]


def test_an_analysis_that_is_quiet_leaves_the_error_stream_empty(
    analysis: list[object], capsys: pytest.CaptureFixture[str]
) -> None:
    handle(["analyze", HEADERS])
    assert capsys.readouterr().err

    handle(["analyze", HEADERS, "--quiet"])

    assert capsys.readouterr().err == ""


def test_generating_from_the_command_line_takes_what_it_was_given() -> None:
    _, request, options = planned(["generate", HEADERS, "-o", OUTPUT, "--contract", CONTRACT])

    assert request.header_directory == Path(HEADERS)  # type: ignore[attr-defined]
    assert request.output_directory == Path(OUTPUT)  # type: ignore[attr-defined]
    assert request.contract_path == Path(CONTRACT)  # type: ignore[attr-defined]
    assert options.include_directories == ()  # type: ignore[attr-defined]


def test_the_front_end_arguments_reach_a_generation(capsys: pytest.CaptureFixture[str]) -> None:
    _, _, options = planned(["generate", HEADERS, "-o", OUTPUT, "-I", "one", "-D", "HOST"])

    assert options.include_directories == (Path("one"),)  # type: ignore[attr-defined]
    assert options.definitions == ("HOST",)  # type: ignore[attr-defined]


def test_an_incomplete_contract_is_accepted_only_when_asked() -> None:
    _, strict, _ = planned(["generate", HEADERS, "-o", OUTPUT])
    _, lenient, _ = planned(["generate", HEADERS, "-o", OUTPUT, "--allow-incomplete-contract"])

    assert not strict.allow_incomplete_contract  # type: ignore[attr-defined]
    assert lenient.allow_incomplete_contract  # type: ignore[attr-defined]


def test_a_definition_says_where_everything_is_so_nothing_is_repeated() -> None:
    """The headers, the contract, the output and the front end, from one file."""
    definition, request, options = planned(["generate", "--definition", DEFINITION])

    assert definition is not None
    assert request.header_directory == definition.header_directory  # type: ignore[attr-defined]
    assert request.output_directory == definition.generated_directory  # type: ignore[attr-defined]
    assert request.contract_path == definition.contract_path  # type: ignore[attr-defined]
    assert options.definitions == definition.parse_definitions  # type: ignore[attr-defined]


class RecordingGeneration:
    """Stands in for the generation, and keeps what reached it."""

    seen: list[tuple[object, object]] = []

    def __init__(self, options: object, progress: object) -> None:
        self._options = options

    def execute(self, request: object) -> object:
        RecordingGeneration.seen.append((self._options, request))
        return object()


@pytest.fixture
def generations(monkeypatch: pytest.MonkeyPatch) -> list[tuple[object, object]]:
    """Nothing is generated and no report is rendered."""
    RecordingGeneration.seen = []
    monkeypatch.setattr(generate_command, "_use_case", RecordingGeneration)
    monkeypatch.setattr(generate_command, "render_generation_report", _render_nothing)
    return RecordingGeneration.seen


def test_what_was_planned_is_what_is_generated(
    generations: list[tuple[object, object]],
) -> None:
    """The decision above is only worth anything if the handler uses it."""
    handle(["generate", HEADERS, "-o", OUTPUT, "-I", "one"])

    options, request = generations[-1]
    assert options.include_directories == (Path("one"),)  # type: ignore[attr-defined]
    assert request.output_directory == Path(OUTPUT)  # type: ignore[attr-defined]


def test_a_generation_that_is_quiet_leaves_the_error_stream_empty(
    generations: list[tuple[object, object]], capsys: pytest.CaptureFixture[str]
) -> None:
    handle(["generate", HEADERS, "-o", OUTPUT])
    assert capsys.readouterr().err

    handle(["generate", HEADERS, "-o", OUTPUT, "--quiet"])

    assert capsys.readouterr().err == ""
