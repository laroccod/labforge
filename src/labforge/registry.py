"""
The value records the Lab stores per registered function.

Dataclasses rather than bare tuples, so page code reads entry.title, not
entry[1]. A shared contract between lab.py, state.py and the pages.
"""

from dataclasses import dataclass


@dataclass
class WorkerSpec:
    """The data-producing function and its control spec."""

    func: callable
    params: dict


@dataclass
class VizSpec:
    """One visualization tab: a figure-returning function plus its controls."""

    func: callable
    title: str
    desc: str
    params: dict


@dataclass
class AnalysisSpec:
    """One analysis tab: a result-returning function plus its controls."""

    func: callable
    title: str
    desc: str
    params: dict
