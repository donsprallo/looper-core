"""Generated artifact repository backed by the local file system."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from looper.domain.model.codegen.generated_artifact import GeneratedArtifact
from looper.domain.repositories import GeneratedArtifactRepository

ENCODING = "utf-8"
NEWLINE = "\n"


class FileSystemArtifactRepository(GeneratedArtifactRepository):
    """Writes generated files below an output root.

    Files are written with newline endings as they were generated, so that a
    build on Windows produces byte identical output to one on Linux.
    """

    def write_all(self, output_directory: Path, artifacts: Sequence[GeneratedArtifact]) -> None:
        """Write every artifact, creating intermediate directories as needed."""
        for artifact in artifacts:
            self._write(output_directory / Path(artifact.relative_path), artifact.content)

    def _write(self, destination: Path, content: str) -> None:
        """Write one file, creating its parent directory first.

        A file that already says exactly this is left alone, untouched
        timestamp and all. Generation runs before every build and the
        adapter it writes is usually the same adapter as last time;
        rewriting it would make every unit that includes the hooks
        header look out of date, which is most of them.
        """
        if _already_holds(destination, content):
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding=ENCODING, newline=NEWLINE)


def _already_holds(destination: Path, content: str) -> bool:
    """Whether the file is byte for byte what would be written.

    Compared as bytes, because that is what is on disk: the newline
    the writer pins down is the one in the content.
    """
    try:
        return destination.read_bytes() == content.encode(ENCODING)
    except OSError:
        return False
