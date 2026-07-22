"""
The value records the Lab stores per registered function.

Dataclasses rather than bare tuples, so page code reads entry.title, not
entry[1]. A shared contract between lab.py, state.py and the pages.
"""

from dataclasses import dataclass, field


@dataclass
class WorkerSpec:
    """
    A data-producing function, its control spec, and the viz/analysis tabs that
    read its output. Each worker owns its own tabs, so a lab with several
    workers gives each one its own visualizations and analyses.
    """

    func: callable
    params: dict
    vizzes: list = field(default_factory=list)
    analyses: list = field(default_factory=list)


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


@dataclass
class TheorySelector:
    """
    The Theory page's control and the callback its value drives the markdown
    through. Its selection is written into the lab's shared context under name,
    so every worker and viz reads the same choice.

    Parameters
    ----------
    name: str
        The shared-context key the selection is stored under.
    label: str
        The control label.
    param: Param
        A normalized choice Param supplying the options and default.
    build: callable
        build(selection) -> markdown, re-rendered whenever the selection changes.
    selects_worker: bool
        When True the options name registered workers, and selecting one makes
        it the active worker — the selector is the model switch, and the
        Simulation page shows the active worker as a single tab.
    """

    name: str
    label: str
    param: object
    build: callable
    selects_worker: bool = False
