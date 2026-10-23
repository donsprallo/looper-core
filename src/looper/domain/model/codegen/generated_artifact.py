"""A single file produced by the generation use cases."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from pathlib import PurePosixPath


@unique
class ArtifactKind(Enum):
    """What role a generated file plays in the simulation build."""

    C_SOURCE = "c_source"
    C_HEADER = "c_header"
    PROTOBUF_SCHEMA = "protobuf_schema"
    PYTHON_CLIENT = "python_client"
    BUILD_SCRIPT = "build_script"
    BUILD_INCLUDE = "build_include"


@dataclass(frozen=True)
class GeneratedArtifact:
    """One generated file, described independently of where it is written.

    The domain decides what to generate and under which relative path. Choosing
    an output root and touching the file system is left to the infrastructure
    layer.

    Attributes:
        relative_path: Output path relative to the generation root.
        kind: Role the file plays in the simulation build.
        content: Complete file content.
    """

    relative_path: PurePosixPath
    kind: ArtifactKind
    content: str

    def __post_init__(self) -> None:
        if self.relative_path.is_absolute():
            raise ValueError(f"Artifact path '{self.relative_path}' must be relative")
        if not self.relative_path.name:
            raise ValueError("An artifact path must name a file")
