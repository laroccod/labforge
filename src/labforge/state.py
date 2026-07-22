"""
LabState: the mutable workspace every page of a running app shares.

Pages are rebuilt fresh on each navigation and the state has no observers, so
anything that must survive a rebuild lives here.
"""

import time
from dataclasses import dataclass, field

from .scan import ScanResult, run_worker


@dataclass
class LabState:
    """
    The mutable workspace of a running Lab.

    Parameters
    ----------
    lab: Lab
        The registrations; read-only from pages.
    worker_values: dict
        Current parsed control values; list-valued entries are scan axes.
    data: object
        The last run's output — the worker's bare return, or a ScanResult.
    n_points: int
        Grid size of the last run (1 for a scalar run, 0 before any run).
    run_summary: str
        Status line shown on the Simulation page.
    viz_values: dict
        {viz title: {kwarg: value}}, persisted across page rebuilds.
    analysis_values: dict
        {analysis title: {kwarg: value}}, persisted across page rebuilds.
    """

    lab: object
    worker_values: dict = None
    data: object = None
    n_points: int = 0
    run_summary: str = ""
    viz_values: dict = field(default_factory=dict)
    analysis_values: dict = field(default_factory=dict)

    def __post_init__(self):
        # Seed every control value from its normalized Param default.
        if self.worker_values is None:
            self.worker_values = defaults(self.lab.worker.params)
        for entry in self.lab.vizzes:
            self.viz_values.setdefault(entry.title, defaults(entry.params))
        for entry in self.lab.analyses:
            self.analysis_values.setdefault(entry.title, defaults(entry.params))

    def has_data(self):
        """True once the worker has produced data; gates Viz and Analysis."""
        return self.n_points > 0

    def run(self):
        """Run the worker over the current values and record a telemetry line."""
        start = time.perf_counter()
        self.data = run_worker(self.lab.worker.func, self.worker_values)
        self.n_points = len(self.data) if isinstance(self.data, ScanResult) else 1
        elapsed = time.perf_counter() - start
        # Report the grid the author actually asked for, not just the point count.
        axes = sum(1 for value in self.worker_values.values() if isinstance(value, list))
        grid = f"{self.n_points} {'POINT' if self.n_points == 1 else 'POINTS'}"
        if axes:
            grid += f" · {axes} {'AXIS' if axes == 1 else 'AXES'}"
        self.run_summary = f"RUN COMPLETE · {grid} · {elapsed:.2f} s"


def defaults(params):
    """Initial control values for a normalized {name: Param} spec."""
    return {name: param.default for name, param in params.items()}
