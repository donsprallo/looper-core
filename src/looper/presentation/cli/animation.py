"""The thing that keeps a spinner turning while the work blocks.

A compiler run is one call that returns when it is finished. Nothing
on the main thread can repaint anything in the meantime, so a second
thread does it: it owns no state, draws nothing itself, and only asks
the display to paint itself again every so often.

It exists for terminals and nowhere else. Where lines cannot be
rewritten there is nothing to animate, and no thread is started.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

#: How often a frame is drawn. Fast enough to look alive, slow enough
#: that a redirected build does not spend its time formatting text.
INTERVAL_SECONDS = 0.1

#: How long stopping waits for the thread to notice. It only ever
#: sleeps for one interval, so this is generous.
JOIN_SECONDS = 1.0


class Animation:
    """Calls one function over and over until it is stopped."""

    def __init__(self, paint: Callable[[], None], interval_seconds: float = INTERVAL_SECONDS):
        self._paint = paint
        self._interval = interval_seconds
        self._stopping = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="looper-progress", daemon=True)

    def start(self) -> None:
        """Begin repainting."""
        self._thread.start()

    def stop(self) -> None:
        """Stop repainting and wait for the last frame to finish."""
        self._stopping.set()
        self._thread.join(timeout=JOIN_SECONDS)

    def _loop(self) -> None:
        """Paint on every interval until asked to stop."""
        while not self._stopping.wait(self._interval):
            self._paint()
