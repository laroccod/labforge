"""
Theory page: markdown prose with $$...$$ blocks rendered as LaTeX images.
"""

import re

import flet as ft

from .. import ui
from ..controls import build_control

EQUATION_BLOCK = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)

EMPTY = "No theory registered — pass a markdown file or string to Lab.set_theory."


def render_source(source):
    """
    Split markdown into prose and equation images.

    Flet's Markdown control has no reliable LaTeX support, so displayed
    equations are carried in $$...$$ blocks and rendered as images instead.
    Inline math should use Unicode symbols in the prose.
    """
    if not source:
        return [ui.placeholder(EMPTY)]
    controls = []
    for index, piece in enumerate(EQUATION_BLOCK.split(source)):
        piece = piece.strip()
        if not piece:
            continue
        # split() alternates prose and captures, so odd indices are the equations.
        # An equation collapses to one line: matplotlib renders each line of a
        # multi-line string separately, and a line with an unmatched $ renders
        # as literal text rather than math.
        controls.append(ui.equation(" ".join(piece.split())) if index % 2 else ui.body(piece))
    return controls


def content(state):
    """The theory controls from the lab's static markdown source."""
    return render_source(state.lab.theory_source)


def section(state, page, on_model_change=None):
    """
    The Theory-page controls: static prose, or a selector driving live markdown.

    When a Theory selector is registered, its choice control writes the shared
    context and its value rebuilds the markdown in place — the mutate-a-mounted-
    Column pattern the result panes use — so the equations follow the selection
    without a navigation. When the selector drives the worker (selects_worker),
    the same change switches the active worker.

    Parameters
    ----------
    on_model_change: callable
        Called after a worker-switching selection commits. The scroll layout
        passes a hook that rebuilds its Simulation and results sections, which
        the pages layout gets for free from its rebuild-on-navigate.
    """
    selector = state.lab.theory_selector
    if selector is None:
        return content(state)
    selection = state.context.get(selector.name, selector.param.default)
    body = ft.Column(spacing=16, controls=render_source(selector.build(selection)))

    def on_change(value):
        # A worker-driving selector switches the active worker before the rest
        # of the lab reads it; downstream sections then reflect the new model.
        if selector.selects_worker and value in state.lab.workers:
            state.set_worker(value)
            if on_model_change is not None:
                on_model_change()
        body.controls = render_source(selector.build(value))
        page.update()

    binding = build_control(selector.name, selector.param, state.context, page, on_change=on_change)
    return [ui.card(binding.row), body]


def build(state, page):
    """Build the Theory page from the lab's static source or its selector."""
    return ui.page_scaffold("Theory", section(state, page))
