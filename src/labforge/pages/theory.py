"""
Theory page: markdown prose with $$...$$ blocks rendered as LaTeX images.
"""

import re

from .. import ui

EQUATION_BLOCK = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)

EMPTY = "No theory registered — pass a markdown file or string to Lab.set_theory."


def content(state):
    """
    The theory controls — prose and equations, or a placeholder when unset.

    Flet's Markdown control has no reliable LaTeX support, so displayed
    equations are carried in $$...$$ blocks and rendered as images instead.
    Inline math should use Unicode symbols in the prose.
    """
    source = state.lab.theory_source
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


def build(state, page):
    """Build the Theory page from the lab's markdown source."""
    return ui.page_scaffold("Theory", content(state))
