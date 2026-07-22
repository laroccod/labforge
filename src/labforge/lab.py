"""
Lab: register a worker, visualizations, analyses and theory, then open the app.
"""

import os

from .param import normalize_spec
from .registry import AnalysisSpec, VizSpec, WorkerSpec
from .theme import DEFAULT as DEFAULT_THEME


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
    """

    def __init__(self, title, page_title=None, icon=""):
        self.title = title
        self.page_title = page_title or title
        self.icon = icon
        self.theory_source = None
        self.worker = None
        self.vizzes = []
        self.analyses = []

    def set_theory(self, source):
        """
        Register the Theory page content.

        Parameters
        ----------
        source: str or Path
            Path to a markdown file, or raw markdown. Displayed equations in
            $$...$$ blocks render as LaTeX images.
        """
        source = os.fspath(source)
        if os.path.isfile(source):
            with open(source, encoding="utf-8") as handle:
                source = handle.read()
        self.theory_source = source

    def add_worker(self, func, spec=None):
        """
        Register the data-producing function.

        Parameters
        ----------
        func: callable
            Called with one scalar per kwarg; a scan calls it once per grid
            point. Its return is the data handed to viz and analysis functions.
        spec: dict
            {kwarg: Param or shorthand str}; unspecced kwargs are inferred from
            their signature defaults.
        """
        # One worker per Lab: a second would need a picker and a workspace stash
        # to switch between their results, which is a larger design than this.
        if self.worker is not None:
            raise ValueError(
                "labforge supports one worker per Lab; already registered "
                f"{self.worker.func.__name__}."
            )
        self.worker = WorkerSpec(func=func, params=normalize_spec(func, spec))

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
        self.vizzes.append(VizSpec(func=func, title=title, desc=desc, params=params))

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
        self.analyses.append(AnalysisSpec(func=func, title=title, desc=desc, params=params))

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
        if self.worker is None:
            raise ValueError("Register a worker with add_worker before opening the lab.")
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
        ft.run(self.build_main(layout=layout, theme=theme), view=views[view], port=port)
