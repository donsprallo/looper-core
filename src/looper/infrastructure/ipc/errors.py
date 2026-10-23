"""Failures raised while talking to a running simulation.

Only the one that belongs to this adapter. A refusal is part of
what every `SimulationSession` promises, whichever adapter is
behind it, so `SimulationRejectedError` lives with the port; being
unable to reach a socket is this adapter's own business.
"""

from __future__ import annotations


class SimulationUnreachableError(ConnectionError):
    """The simulation could not be reached or closed the connection."""


class ProtocolMismatchError(Exception):
    """The simulation speaks a version of the control protocol this client does not.

    Reaching the socket is not the same as being able to read what comes
    back. A field that moved is not a parse error -- it is a value read
    into the wrong field -- so a client that can tell refuses rather than
    reports something plausible and wrong.

    Deliberately not a `ConnectionError`. Code that cannot reach a
    simulation waits and tries again, which is the right answer to a
    simulation that has not finished starting and the wrong one here:
    the two will still disagree in ten seconds. Keeping it outside that
    family makes a retry loop report the mismatch instead of timing out
    on it.
    """
