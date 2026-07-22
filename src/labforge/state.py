"""
LabState: the mutable workspace every page of a running app shares.

Pages are rebuilt fresh on each navigation and the state has no observers, so
anything that must survive a rebuild lives here. A multi-worker lab keeps one
Workspace per worker and swaps the active one, so switching workers and back
restores exactly what was there.
"""

import time
from dataclasses import dataclass, field

from .scan import ScanResult, run_worker


@dataclass
class Workspace:
    """
    One worker's saved state — its controls, last result and per-tab kwargs.

    Parameters
    ----------
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

    worker_values: dict
    data: object = None
    n_points: int = 0
    run_summary: str = ""
    viz_values: dict = field(default_factory=dict)
    analysis_values: dict = field(default_factory=dict)


def make_workspace(spec):
    """A fresh Workspace seeded from a WorkerSpec's normalized defaults."""
    workspace = Workspace(worker_values=defaults(spec.params))
    for entry in spec.vizzes:
        workspace.viz_values[entry.title] = defaults(entry.params)
    for entry in spec.analyses:
        workspace.analysis_values[entry.title] = defaults(entry.params)
    return workspace


@dataclass
class LabState:
    """
    The mutable workspace of a running Lab.

    Holds one Workspace per registered worker and tracks which is active; the
    worker_values/data/... properties always read the active one, so pages need
    not know whether the lab has one worker or several.

    Parameters
    ----------
    lab: Lab
        The registrations; read-only from pages.
    active: str
        The active worker's name; defaults to the first registered.
    workspaces: dict
        {worker name: Workspace}; one per worker, seeded on construction.
    """

    lab: object
    active: str = None
    workspaces: dict = None
    context: dict = None
    last_run: str = None
    shared_viz_values: dict = None
    shared_analysis_values: dict = None

    def __post_init__(self):
        if self.active is None:
            # A worker-driving selector's default is the active worker, so the
            # app opens on the model the Theory dropdown shows; else the first.
            if self.lab.selects_worker:
                self.active = self.lab.theory_selector.param.default
            else:
                self.active = next(iter(self.lab.workers), None)
        if self.workspaces is None:
            self.workspaces = {
                name: make_workspace(spec) for name, spec in self.lab.workers.items()
            }
        # One shared context per session (never module-level), seeded with the
        # Theory selector's default so workers can read it before any interaction.
        if self.context is None:
            self.context = {}
            selector = self.lab.theory_selector
            if selector is not None:
                self.context[selector.name] = selector.param.default
        # Lab-level tab values, shared across workers in "tabs" view.
        if self.shared_viz_values is None:
            self.shared_viz_values = {v.title: defaults(v.params) for v in self.lab.shared_vizzes}
        if self.shared_analysis_values is None:
            self.shared_analysis_values = {
                a.title: defaults(a.params) for a in self.lab.shared_analyses
            }

    @property
    def tabbed(self):
        """True when workers render as Simulation-page tabs with shared tabs."""
        return self.lab.worker_view == "tabs"

    @property
    def workspace(self):
        """The active worker's Workspace."""
        return self.workspaces[self.active]

    @property
    def worker(self):
        """The active WorkerSpec."""
        return self.lab.workers[self.active]

    @property
    def vizzes(self):
        """The visualization tabs: lab-level in tabs view, else the active worker's."""
        return self.lab.shared_vizzes if self.tabbed else self.worker.vizzes

    @property
    def analyses(self):
        """The analysis tabs: lab-level in tabs view, else the active worker's."""
        return self.lab.shared_analyses if self.tabbed else self.worker.analyses

    # The workspace fields the pages read and write straight through, so a page
    # touching state.worker_values or state.data always sees the active worker.
    @property
    def worker_values(self):
        return self.workspace.worker_values

    @property
    def data(self):
        # In tabs view the shared viz read the most recently run worker's output.
        if self.tabbed:
            return self.workspaces[self.last_run].data if self.last_run else None
        return self.workspace.data

    @property
    def n_points(self):
        return self.workspace.n_points

    @property
    def run_summary(self):
        return self.workspace.run_summary

    @property
    def viz_values(self):
        return self.shared_viz_values if self.tabbed else self.workspace.viz_values

    @property
    def analysis_values(self):
        return self.shared_analysis_values if self.tabbed else self.workspace.analysis_values

    def set_worker(self, name):
        """Switch the active worker; each keeps its own stashed workspace."""
        if name not in self.workspaces:
            raise KeyError(f"no worker named {name!r}.")
        self.active = name

    def has_data(self):
        """True once a worker has produced data; gates Viz and Analysis."""
        if self.tabbed:
            return any(workspace.n_points > 0 for workspace in self.workspaces.values())
        return self.workspace.n_points > 0

    def run(self, worker_name=None):
        """Run one worker over its values and record a telemetry line.

        Parameters
        ----------
        worker_name: str
            The worker to run; the active worker when omitted. Running marks it
            the most recently run, which the shared viz of a tabs-view lab read.
        """
        name = worker_name or self.active
        workspace = self.workspaces[name]
        spec = self.lab.workers[name]
        start = time.perf_counter()
        workspace.data = run_worker(spec.func, workspace.worker_values, context=self.context)
        workspace.n_points = len(workspace.data) if isinstance(workspace.data, ScanResult) else 1
        elapsed = time.perf_counter() - start
        # Report the grid the author actually asked for, not just the point count.
        axes = sum(1 for value in workspace.worker_values.values() if isinstance(value, list))
        grid = f"{workspace.n_points} {'POINT' if workspace.n_points == 1 else 'POINTS'}"
        if axes:
            grid += f" · {axes} {'AXIS' if axes == 1 else 'AXES'}"
        workspace.run_summary = f"RUN COMPLETE · {grid} · {elapsed:.2f} s"
        self.last_run = name


def defaults(params):
    """Initial control values for a normalized {name: Param} spec."""
    return {name: param.default for name, param in params.items()}
