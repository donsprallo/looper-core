"""Which directory a measured function was compiled from, and what that means.

The debug information says where every function's source file lives. A
build definition already says which directories hold what. Putting the
two together is the whole of the classification, which is why nobody has
to keep a list of names in step with the code.

Order matters, and only in one place: the generated adapter lives inside
the project that owns the device model, so the narrower directories are
asked first and the project's own source only afterwards.

The question is asked once per measured function per reading, and a
profile has hundreds of those several times a second. So neither half
of the comparison is prepared twice: the directories are folded when
the layout is made, and the answer for a source file is kept once it
has been worked out. A layout cannot change, and neither can where a
file lies within it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePath

from looper.domain.model.sources.function_origin import FunctionOrigin


@dataclass(frozen=True)
class SourceLayout:
    """Where each part of a simulation keeps its sources.

    Attributes:
        adapter: Where generation wrote the simulated adapter.
        runtime: Where the looper runtime lives.
        components: Where the shipped device components live.
        device_model: The project's own sources, which stand in for a board.
        firmware: The firmware under test.
    """

    adapter: tuple[PurePath, ...] = field(default_factory=tuple)
    runtime: tuple[PurePath, ...] = field(default_factory=tuple)
    components: tuple[PurePath, ...] = field(default_factory=tuple)
    device_model: tuple[PurePath, ...] = field(default_factory=tuple)
    firmware: tuple[PurePath, ...] = field(default_factory=tuple)

    #: Every directory as the prefix a file is tested against, in the
    #: order they are asked. Derived, so it takes no part in equality.
    _claims: tuple[tuple[str, FunctionOrigin], ...] = field(
        init=False, repr=False, compare=False, default_factory=tuple
    )
    #: What has already been worked out, by folded source path.
    _known: dict[str, FunctionOrigin] = field(
        init=False, repr=False, compare=False, default_factory=dict
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "_claims",
            tuple(
                (_claimed(directory), origin)
                for directories, origin in self._in_order()
                for directory in directories
            ),
        )

    def origin_of(self, source: PurePath | None) -> FunctionOrigin:
        """Say which part of the simulation a source file belongs to.

        A function with no source at all came out of a library: it was
        linked in already compiled, which is also why it carries no
        debug information and could never have been instrumented.

        A function with a source that no directory claims was compiled
        here from a file this layout was not told about, and the only
        thing it can be is firmware. Saying so is what lets a client
        that knows nothing of the build definition still separate the
        library from the rest.
        """
        if source is None:
            return FunctionOrigin.LIBRARY
        folded = _folded(source)
        remembered = self._known.get(folded)
        if remembered is not None:
            return remembered
        decided = self._decide(folded)
        self._known[folded] = decided
        return decided

    def _decide(self, folded: str) -> FunctionOrigin:
        """Which directory claims a file, the first time it is asked."""
        for claimed, origin in self._claims:
            if folded.startswith(claimed):
                return origin
        return FunctionOrigin.FIRMWARE

    def _in_order(self) -> tuple[tuple[tuple[PurePath, ...], FunctionOrigin], ...]:
        """The directories to test, narrowest claim first."""
        return (
            (self.adapter, FunctionOrigin.ADAPTER),
            (self.runtime, FunctionOrigin.RUNTIME),
            (self.components, FunctionOrigin.COMPONENT),
            (self.device_model, FunctionOrigin.DEVICE_MODEL),
            (self.firmware, FunctionOrigin.FIRMWARE),
        )


def _claimed(directory: PurePath) -> str:
    """One directory as a prefix a file path is tested against.

    Windows writes the same path in more than one case, and a compiler
    and a build definition need not agree on which, so the comparison is
    made on the folded form.
    """
    return _folded(directory).rstrip("\\") + "\\"


def _folded(path: PurePath) -> str:
    """One spelling of a path, for comparing two of them."""
    return str(path).replace("/", "\\").casefold()
