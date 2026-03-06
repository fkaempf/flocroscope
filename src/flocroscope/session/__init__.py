"""Experiment session management.

Provides lifecycle management for experimental sessions, including
trial tracking, event logging, and metadata persistence.  Sessions
bridge the stimulus system, communications hub, and future
Flomington integration.

Example::

    from flocroscope.session import Session

    session = Session(config=my_config)
    session.start()
    session.begin_trial(metadata={"genotype": "w1118"})
    # ... run stimulus loop ...
    session.end_trial()
    session.save()
    session.stop()
"""

from flocroscope.session.session import Session

__all__ = ["Session"]
