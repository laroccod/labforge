"""
Lab: register a worker, visualizations, analyses and theory, then open the app.
"""

import os

from .param import Param, normalize_spec, validate_param
from .registry import AnalysisSpec, TheorySelector, VizSpec, WorkerSpec
from .theme import DEFAULT as DEFAULT_THEME

WORKER_VIEWS = ("panels", "tabs")


class Lab:
    """
    A four-page scientific desktop app assembled from plain functions.

    Every registration is validated on the spot — spec keys checked against the
    function signature, defaults resolved — so a malformed app fails at
    assembly rather than mid-navigation.

    Parameters
    ----------
    title: str
        App name shown in the top bar.
    page_title: str
        Window title; defaults to title.
    icon: str
        A Flet icon constant for the top-bar app mark; a volume mark by default.
    worker_view: str
        "panels" (default): each worker owns its own viz/analysis panels, and
        one worker is active at a time — several workers are switched with a
        selects_worker Theory selector (see set_theory_selector). "tabs": the
        workers render as tabs on the Simulation page against one shared context,
        and add_viz/add_analysis register lab-level tabs shared across every
        worker. Either way there is no top-bar worker dropdown.
    """

    def __init__(self, title, page_title=None, icon="", worker_view="panels"):
        if worker_view not in WORKER_VIEWS:
            raise ValueError(
                f"worker_view must be one of {sorted(WORKER_VIEWS)}, got {worker_view!r}."
            )
        self.title = title
        self.page_title = page_title or title
        self.icon = icon
        self.worker_view = worker_view
        self.theory_source = None
        # The Theory-page control (a choice) whose value drives the theory
        # markdown and the shared context; None keeps the static-source page.
        self.theory_selector = None
        # Insertion-ordered {name: WorkerSpec}. Each worker keeps its own
        # workspace and tabs; last_worker is the one add_viz/add_analysis attach to.
        self.workers = {}
        self.last_worker = None
        # Lab-level tabs shared across all workers, used only in "tabs" view.
        self.shared_vizzes = []
        self.shared_analyses = []

    def set_theory(self, source):
        """
        Register the Theory page content.

        A string that names no existing file but clearly meant to — a Path
        object, or a whitespace-free string ending in ".md" — raises here rather
        than silently rendering the mistyped path as a one-line prose page.

        Parameters
        ----------
        source: str or Path
            Path to a markdown file, or raw markdown. Displayed equations in
            $$...$$ blocks render as LaTeX images.
        """
        looks_like_path = isinstance(source, os.PathLike)
        text = os.fspath(source)
        if os.path.isfile(text):
            with open(text, encoding="utf-8") as handle:
                self.theory_source = handle.read()
            return
        # A whitespace-free string ending in .md is a path typo, not prose.
        looks_like_path = looks_like_path or (
            text.endswith(".md") and not any(c.isspace() for c in text)
        )
        if looks_like_path:
            raise ValueError(f"set_theory: no such file {text!r}.")
        self.theory_source = text

    def set_theory_selector(self, name, param, theory, label=None, selects_worker=False):
        """
        Register a choice control on the Theory page whose value drives the
        markdown and the lab's shared context.

        The selection is written into the shared context under name (so every
        worker and viz reads the same choice) and passed to theory(selection),
        whose returned markdown — $$...$$ blocks and all — replaces the theory
        prose whenever the selection changes. Coexists with set_theory: the
        selector takes precedence when both are set.

        Parameters
        ----------
        name: str
            The shared-context key the selection is stored under.
        param: Param
            A choice Param (kind "choice", options=[...]); its default is the
            starting selection, falling back to the first option.
        theory: callable
            theory(selection) -> markdown, called on build and on every change.
        label: str
            The control label; the name when omitted.
        selects_worker: bool
            When True the options must name registered workers (checked at
            build), and choosing one makes it the active worker. The top-bar
            worker dropdown is then dropped — this selector is the model switch —
            and the Simulation page shows the active worker as a single tab. The
            worker-name check is deferred to build so the selector may be
            registered before the workers it names.
        """
        if not isinstance(param, Param) or param.kind != "choice":
            raise ValueError("set_theory_selector needs a choice Param (kind='choice').")
        if param.default is None and param.options:
            param.default = param.options[0]
        # The selector's label is the control's label; carry it onto the param,
        # which is what build_control reads at draw time.
        param.label = label or name
        validate_param(theory, name, param, allow_scan=False)
        self.theory_selector = TheorySelector(
            name=name, label=label or name, param=param, build=theory, selects_worker=selects_worker
        )

    @property
    def selects_worker(self):
        """True when a Theory selector doubles as the active-worker switch."""
        return self.theory_selector is not None and self.theory_selector.selects_worker

    def add_worker(self, func, spec=None, name=None):
        """
        Register a data-producing function.

        Call it more than once to build a multi-worker lab: each worker keeps its
        own workspace, and add_viz/add_analysis after each call attach that
        worker's tabs. Several workers must be made switchable with a
        selects_worker Theory selector or worker_view="tabs" (checked at build).

        Parameters
        ----------
        func: callable
            Called with one scalar per kwarg; a scan calls it once per grid
            point. Its return is the data handed to viz and analysis functions.
        spec: dict
            {kwarg: Param or shorthand str}; unspecced kwargs are inferred from
            their signature defaults.
        name: str
            Selector label and stash key; defaults to func.__name__. Must be
            unique within the lab.
        """
        name = name or func.__name__
        if name in self.workers:
            raise ValueError(f"a worker named {name!r} is already registered.")
        self.workers[name] = WorkerSpec(func=func, params=normalize_spec(func, spec))
        self.last_worker = name

    def add_viz(self, func, title, desc="", spec=None):
        """
        Register a visualization tab.

        Parameters
        ----------
        func: callable
            func(data, **kwargs) returning a matplotlib Figure or (fig, ax).
            data is the worker's bare return, or a ScanResult after a scan.
        title: str
            Tab label.
        desc: str
            Short markdown note shown above the controls.
        spec: dict
            {kwarg: Param or shorthand str} for the kwargs after data.
        """
        params = normalize_spec(func, spec, skip_first=True, allow_scan=False)
        entry = VizSpec(func=func, title=title, desc=desc, params=params)
        # In "tabs" view the viz are lab-level, shared across every worker; in
        # "panels" view each worker owns its own, so attach to the last one.
        if self.worker_view == "tabs":
            self.shared_vizzes.append(entry)
        else:
            self.current_worker().vizzes.append(entry)

    def add_analysis(self, func, title, desc="", spec=None):
        """
        Register an analysis tab.

        Parameters
        ----------
        func: callable
            func(data, **kwargs) returning a dict (two-column table), a list of
            dicts (table), a string (markdown), or a matplotlib figure.
        title: str
            Tab label.
        desc: str
            Short markdown note shown above the controls.
        spec: dict
            {kwarg: Param or shorthand str} for the kwargs after data.
        """
        params = normalize_spec(func, spec, skip_first=True, allow_scan=False)
        entry = AnalysisSpec(func=func, title=title, desc=desc, params=params)
        if self.worker_view == "tabs":
            self.shared_analyses.append(entry)
        else:
            self.current_worker().analyses.append(entry)

    def current_worker(self):
        """The worker add_viz/add_analysis attach to — the most recently added."""
        if self.last_worker is None:
            raise ValueError("Register a worker with add_worker before adding tabs.")
        return self.workers[self.last_worker]

    def build_main(self, layout="pages", theme=DEFAULT_THEME):
        """
        Return the Flet main(page) entry point; also the headless test seam.

        Parameters
        ----------
        layout: str
            "pages" or "scroll", as in open().
        theme: str
            A key of labforge.themes(), as in open().

        Returns
        -------
        A main(page) callable.
        """
        if not self.workers:
            raise ValueError("Register a worker with add_worker before opening the lab.")
        # A worker-driving selector's options must name real workers; checked
        # here, once both are registered, not at set_theory_selector time.
        if self.selects_worker:
            unknown = [opt for opt in self.theory_selector.param.options if opt not in self.workers]
            if unknown:
                raise ValueError(
                    f"selects_worker selector options must name workers; unknown: {unknown}."
                )
        # There is no top-bar worker dropdown, so several workers need an explicit
        # way to choose among them: a model selector or the tabs view.
        if len(self.workers) > 1 and self.worker_view != "tabs" and not self.selects_worker:
            raise ValueError(
                "Several workers need a way to choose among them: either a "
                "selects_worker=True Theory selector (set_theory_selector) or "
                "worker_view='tabs'."
            )
        # Imported here, not at module scope, so registration and validation
        # never pay for Flet's UI layer.
        from .shell import build_main

        return build_main(self, layout=layout, theme=theme)

    def open(self, view="app", layout="pages", port=0, theme=DEFAULT_THEME):
        """
        Launch the app.

        Parameters
        ----------
        view: str
            "app" opens a native desktop window; "browser" serves the app and
            opens it in the default web browser — handy for iterating, since a
            served app is reachable from any browser on a stable URL.
        layout: str
            "pages" navigates the four pages with a rail; "scroll" shows the
            whole lab as one continuous scrolling page.
        port: int
            Port for the "browser" view; 0 lets the OS pick a free one. With a
            fixed port the app stays at http://localhost:<port> across relaunches.
        theme: str
            The colour scheme: any key of labforge.themes(), which lists each
            with a one-line note. Sets the chrome, the plot palette and the
            equation ink together, so a figure drawn with labforge.palette()
            follows it.
        """
        import flet as ft

        views = {"app": ft.AppView.FLET_APP, "browser": ft.AppView.WEB_BROWSER}
        if view not in views:
            raise ValueError(f"view must be one of {sorted(views)}, got {view!r}.")
        # assets_dir serves the bundled fonts (ui.FONT_ASSETS) to both the native
        # client and the browser, so page.fonts resolves the same faces either way.
        assets = os.path.join(os.path.dirname(__file__), "assets")
        ft.run(
            self.build_main(layout=layout, theme=theme),
            view=views[view],
            port=port,
            assets_dir=assets,
        )
