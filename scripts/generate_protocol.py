"""Regenerate the protobuf bindings from the control protocol schema."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import looper_rt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# The schema belongs to the runtime, which owns the wire format; the
# bindings generated from it belong here, because this is what imports them.
SCHEMA_DIRECTORY = Path(looper_rt.__file__).parent / "proto"
OUTPUT_DIRECTORY = PROJECT_ROOT / "src" / "looper" / "infrastructure" / "ipc" / "generated"
SCHEMA = SCHEMA_DIRECTORY / "looper_control.proto"


def main() -> int:
    """Run protoc and report whether the bindings were written."""
    command = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"-I{SCHEMA_DIRECTORY}",
        f"--python_out={OUTPUT_DIRECTORY}",
        f"--pyi_out={OUTPUT_DIRECTORY}",
        str(SCHEMA),
    ]
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        print("protoc failed", file=sys.stderr)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
