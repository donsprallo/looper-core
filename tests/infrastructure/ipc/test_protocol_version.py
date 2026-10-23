"""The client and the runtime have to speak the same protocol version.

These are two distributions now, so they can be installed at versions
that do not match. The number the client compares against is written by
hand here and the number the runtime answers with is written by hand in
C, which is exactly the kind of pair that drifts.

Whether the schema and the runtime number their fields alike is checked
in `looper-rt`, where both files live. What is checked here is the half
of the agreement that spans the two projects.
"""

from __future__ import annotations

import re
from pathlib import Path

import looper_rt
import pytest

from looper.infrastructure.ipc.errors import ProtocolMismatchError
from looper.infrastructure.ipc.protobuf_session import (
    PROTOCOL_VERSION,
    UNVERSIONED,
    ProtobufSimulationSession,
)

PROTOCOL_HEADER = Path(looper_rt.__file__).parent / "runtime" / "include" / "looper_protocol.h"
RUNTIME_VERSION = re.compile(r"^#define\s+LOOPER_PROTOCOL_VERSION\s+(\d+)u\s*$", re.MULTILINE)

check = ProtobufSimulationSession._check_protocol


def runtime_version() -> int:
    """Return the version the installed runtime answers COMMAND_HELLO with."""
    found = RUNTIME_VERSION.search(PROTOCOL_HEADER.read_text(encoding="utf-8"))
    assert found is not None, f"no LOOPER_PROTOCOL_VERSION in {PROTOCOL_HEADER}"
    return int(found.group(1))


def test_the_client_speaks_the_version_the_installed_runtime_answers_with() -> None:
    """Raising one without the other would refuse every simulation."""
    assert runtime_version() == PROTOCOL_VERSION


def test_a_matching_version_is_accepted() -> None:
    check(PROTOCOL_VERSION)


def test_a_simulation_built_before_the_version_says_so() -> None:
    """Zero is "too old to say", which is its own thing to report."""
    with pytest.raises(ProtocolMismatchError, match="before the control protocol"):
        check(UNVERSIONED)


def test_a_version_this_client_cannot_read_is_refused() -> None:
    """Naming both numbers is what tells the reader which half to rebuild."""
    with pytest.raises(ProtocolMismatchError, match="speaks control protocol 99"):
        check(99)
