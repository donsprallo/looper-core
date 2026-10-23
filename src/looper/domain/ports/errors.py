"""Failures that are part of what a port promises.

A refusal is not a breakage, and the difference is the whole of the
contract a client is written against: a simulation that will not
drive an output pin has answered the question, while a simulation
that has stopped answering has not. A client shows the first beside
the form that asked for it and carries on; the second ends the
session.

So the type that says "refused" belongs with the port rather than
with whichever adapter happens to be plugged into it. Named by the
adapter, every client would have to know which adapter it was given
before it could tell the two apart -- and a graphical client would
be importing a protocol implementation to catch an error about a
pin.

It is a `ValueError` because that is what a refusal is: the request
named something the simulation will not do, and the ports have
always documented it that way. An adapter that validates before it
sends and one that lets the simulation answer therefore raise the
same thing.
"""

from __future__ import annotations


class SimulationRejectedError(ValueError):
    """The simulation refused a request and explained why."""
