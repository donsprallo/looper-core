"""A call tree, ready to be drawn as a flame graph.

Flattened on purpose. The domain holds a tree, which is the right
shape for deciding what hangs under what; a drawing wants a list of
rectangles it can paint in one pass and pick from without walking
anything. Turning the one into the other is done once, where the
geometry is decided, rather than on every repaint.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class FrameView(BaseModel):
    """One function, reached one way, as a bar.

    Attributes:
        name: Name the debug information gives it.
        origin: Which part of the simulation it belongs to, which is
            what the bar is coloured by.
        depth: How many frames are below it, the outermost being nought.
        start: Where its bar begins, as a share of the whole window.
        width: How wide it is, as the same share.
        calls: How often it was entered by this path.
        total: Host time spent here, as it is shown.
        own: The part of that which was its own work, as it is shown.
        share: What part of the window it accounts for.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    origin: str
    depth: int
    start: float
    width: float
    calls: int = 0
    total: str = ""
    own: str = ""
    share: float = 0.0

    @property
    def caption(self) -> str:
        """What a reader is told when they point at it.

        The origin is named as well as drawn, because a colour is
        learnt by being told once what it means.
        """
        spent = f"{self.total} ({self.share:.1%})"
        return f"{self.name}  {spent}, {self.calls} calls, {self.own} own  --  {self.origin}"


class FlameView(BaseModel):
    """Everything that ran in one window, as bars.

    Attributes:
        frames: Every bar, outermost first, then left to right.
        depth: How deep the deepest path went.
        total: Host time the window accounts for, as it is shown.
        note: What is worth saying about the whole of it, or empty.
        is_watched: Whether the paths were being followed at all.
    """

    model_config = ConfigDict(frozen=True)

    frames: tuple[FrameView, ...] = ()
    depth: int = 0
    total: str = ""
    note: str = ""
    is_watched: bool = False

    @property
    def is_empty(self) -> bool:
        """Whether there is nothing to draw."""
        return not self.frames
