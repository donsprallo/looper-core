"""A channel nothing has written, told apart from one reading zero.

The two look identical on a screen and mean entirely different things:
one is a measurement that happens to be zero, the other is a value the
firmware was never asked to produce. Saying "0 W" for the second sends
somebody looking for a wiring fault that is not there.
"""

from __future__ import annotations

from simulation_doubles import RecordingSession

from looper.application.queries import ObserveChannels
from looper.domain.model.simulation import AnalogChannel, ChannelDirection


def a_channel(label: str, value: float = 0.0, has_value: bool = True) -> AnalogChannel:
    """One registered channel."""
    return AnalogChannel(
        identifier=0,
        label=label,
        unit="W",
        direction=ChannelDirection.OUTPUT,
        value=value,
        has_value=has_value,
    )


def test_a_channel_that_published_zero_shows_zero() -> None:
    session = RecordingSession()
    session.channels = (a_channel("P1A", value=0.0),)

    assert ObserveChannels(session).execute()[0].display_value == "0 W"


def test_a_channel_that_never_published_says_so() -> None:
    session = RecordingSession()
    session.channels = (a_channel("POWER", has_value=False),)

    view = ObserveChannels(session).execute()[0]

    assert view.is_silent
    assert view.display_value == "no data"


def test_a_published_value_is_shown_with_its_unit() -> None:
    session = RecordingSession()
    session.channels = (a_channel("POWER", value=12.5),)

    assert ObserveChannels(session).execute()[0].display_value == "12.5 W"


def test_the_domain_says_plainly_whether_a_channel_is_silent() -> None:
    assert a_channel("POWER", has_value=False).is_silent
    assert not a_channel("P1A").is_silent
