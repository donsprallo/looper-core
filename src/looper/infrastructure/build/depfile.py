"""Reading what a compiler said an object file was built from.

`-MMD` makes the compiler write, beside each object, the list of files
that went into it: the source and every header it pulled in, project
headers and all, leaving out the ones that came from the system. That
list is the only honest answer to "does this unit have to be compiled
again", because nothing else knows which header a unit includes four
levels down.

The format is a makefile rule, and parsing it is two awkward details:
lines are continued with a trailing backslash, and spaces inside a
path are escaped with one. A path that is misread names a file that
does not exist, which a caller reads as "rebuild" -- the safe way to
be wrong.
"""

from __future__ import annotations

import re
from pathlib import Path

#: A backslash at the end of a line continues the rule on the next.
CONTINUATION = re.compile(r"\\\r?\n")

#: Whitespace separates prerequisites, unless it was escaped.
SEPARATOR = re.compile(r"(?<!\\)\s+")


def prerequisites(record: Path) -> tuple[Path, ...]:
    """Every file the object was built from, as the compiler recorded it.

    Args:
        record: The dependency file written beside the object.

    Returns:
        The files, or nothing at all when there is no readable record.
        Nothing is not "depends on nothing": it is "do not know".
    """
    try:
        text = record.read_text(encoding="utf-8")
    except OSError:
        return ()
    return tuple(Path(name) for name in _after_the_target(text))


def _after_the_target(text: str) -> list[str]:
    """The prerequisites of the one rule a dependency file holds.

    The target is the object path and ends in a colon -- including on
    Windows, where the path begins with one as well, which is why the
    first token ending in a colon is what is looked for rather than
    the first colon.
    """
    tokens = [one for one in SEPARATOR.split(CONTINUATION.sub(" ", text).strip()) if one]
    for index, token in enumerate(tokens):
        if token.endswith(":"):
            return [_unescaped(one) for one in tokens[index + 1 :]]
    return []


def _unescaped(token: str) -> str:
    """One path as it is actually spelled on disk."""
    return token.replace("\\ ", " ").replace("$$", "$")
