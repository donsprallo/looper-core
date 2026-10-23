"""The ``looper-cli`` command surface."""

from __future__ import annotations

from pathlib import Path

import pytest

from looper.presentation.cli.main import build_parser

GUI_ARGUMENTS = ["gui", "--port", "45771"]


def test_the_cli_offers_the_five_file_based_commands() -> None:
    parser = build_parser()

    assert parser.parse_args(["analyze", "Inc"]).command == "analyze"
    assert parser.parse_args(["generate", "Inc", "-o", "out"]).command == "generate"
    assert parser.parse_args(["build"]).command == "build"
    assert parser.parse_args(["run"]).command == "run"
    assert parser.parse_args(["audit"]).command == "audit"


def test_the_project_based_commands_default_to_looper_toml() -> None:
    parser = build_parser()

    assert parser.parse_args(["build"]).definition == Path("looper.toml")
    assert parser.parse_args(["run"]).definition == Path("looper.toml")
    assert parser.parse_args(["audit"]).definition == Path("looper.toml")


def test_run_passes_the_clock_and_port_through() -> None:
    arguments = build_parser().parse_args(["run", "--port", "45771", "--virtual"])

    assert arguments.port == 45771
    assert arguments.virtual
    assert not arguments.no_build


def test_the_inspector_is_not_a_subcommand() -> None:
    """The window is reachable only as looper-gui, never through the CLI."""
    with pytest.raises(SystemExit):
        build_parser().parse_args(GUI_ARGUMENTS)


def test_a_command_is_required() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_every_command_can_be_asked_to_work_quietly() -> None:
    """The flag sits on the command, because that is where people type it."""
    parser = build_parser()

    assert parser.parse_args(["build", "--quiet"]).quiet
    assert parser.parse_args(["run", "-q"]).quiet
    assert parser.parse_args(["audit", "--quiet"]).quiet
    assert parser.parse_args(["analyze", "Inc", "--quiet"]).quiet
    assert parser.parse_args(["generate", "Inc", "-o", "out", "--quiet"]).quiet


def test_the_progress_display_is_on_unless_it_is_turned_off() -> None:
    assert not build_parser().parse_args(["build"]).quiet


def test_a_build_can_be_told_to_compile_everything_again() -> None:
    """The way out when the build guesses that something is up to date."""
    parser = build_parser()

    assert parser.parse_args(["build", "--rebuild"]).rebuild
    assert parser.parse_args(["run", "--rebuild"]).rebuild
    assert not parser.parse_args(["build"]).rebuild
