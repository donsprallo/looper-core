"""The shape of a set of measurements, apart from what was measured."""

from __future__ import annotations

from looper.domain.model.measurement.distribution import (
    BUCKET_COUNT,
    Bucket,
    Distribution,
    bucket_of,
    distribute,
)

__all__ = [
    "BUCKET_COUNT",
    "Bucket",
    "Distribution",
    "bucket_of",
    "distribute",
]
