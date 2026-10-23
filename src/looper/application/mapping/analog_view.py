"""Mapping of analog state onto the client facing views."""

from __future__ import annotations

from looper.application.dto.analog_view import ChannelView, SampleView, SignalView, TraceView
from looper.domain.model.simulation import AnalogChannel, AnalogSample, SignalDefinition


def build_channel_view(channel: AnalogChannel) -> ChannelView:
    """Translate one observed channel into its view."""
    return ChannelView(
        channel_id=channel.identifier,
        name=channel.display_name,
        unit=channel.unit,
        direction=channel.direction.value,
        value=channel.value,
        is_drivable=channel.is_drivable_by_client,
        is_silent=channel.is_silent,
        signal=build_signal_view(channel.signal),
    )


def build_signal_view(signal: SignalDefinition) -> SignalView:
    """Translate one signal definition into its view."""
    return SignalView(
        waveform=signal.waveform.value,
        amplitude=signal.amplitude,
        offset=signal.offset,
        frequency_hz=signal.frequency_hz,
        phase_degrees=signal.phase_degrees,
    )


def build_trace_view(samples: tuple[AnalogSample, ...], next_sequence: int) -> TraceView:
    """Translate a batch of recorded samples into its view."""
    return TraceView(
        samples=tuple(_build_sample_view(sample) for sample in samples),
        next_sequence=next_sequence,
    )


def _build_sample_view(sample: AnalogSample) -> SampleView:
    """Translate one recorded sample into its view."""
    return SampleView(
        channel_id=sample.channel,
        seconds=sample.seconds,
        value=sample.value,
        sequence=sample.sequence,
    )
