"""What the use cases call the steps they announce.

The listener itself is a domain port, because the compiler driver
reports through it too. What is here is the vocabulary: the step names
that more than one use case says, so that `build` and `audit` do not
call the same work two different things, and the one piece of grammar
they all need.
"""

from __future__ import annotations

#: Reading the TOML that describes the project.
READING_DEFINITION = "Reading the build definition"

#: Parsing the adapter headers, which is the slow part of every command
#: that touches a compiler front end.
READING_HEADERS = "Reading the adapter headers"

#: Reading the contract that says what the declarations mean.
READING_CONTRACT = "Reading the contract"


def counted(count: int, noun: str) -> str:
    """A number and what it counts, pluralised the way a person would.

    Every noun a step reports takes a plain -s, so that is all this
    does. A step that needs more than that can write its own words.
    """
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"
