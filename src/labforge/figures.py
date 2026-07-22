"""
Serialize the author's matplotlib figures to base64 PNGs, plus an optional
house style.
"""

import base64
import io

import matplotlib

matplotlib.use("Agg")  # render to a buffer; no GUI backend on the UI thread
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from . import theme

RENDER_DPI = 150


def palette():
    """
    The active Theme, for an author colouring their own figure; its data /
    model / highlight / ink / grid fields are the plot palette. Read at call
    time rather than bound at import, so a figure drawn with palette().data
    follows whichever theme open(theme=...) selected.
    """
    return theme.active()


def is_figure(value):
    """True for a matplotlib Figure or a (fig, ...) tuple, the two viz returns."""
    if isinstance(value, tuple):
        return bool(value) and isinstance(value[0], Figure)
    return isinstance(value, Figure)


def unpack_figure(value):
    """Extract the Figure from a viz return: a bare Figure or a (fig, ...) tuple."""
    if not is_figure(value):
        raise TypeError(
            f"Expected a matplotlib Figure or a (fig, ax) tuple, got {type(value).__name__}."
        )
    return value[0] if isinstance(value, tuple) else value


def figure_to_base64(fig):
    """
    Serialize a matplotlib figure to a base64 PNG and close it, so repeated
    renders never leak pyplot state.
    """
    buffer = io.BytesIO()
    # transparent=True clears the figure and axes patches so the app surface
    # shows through; the pale ink still reads on the dark theme.
    fig.savefig(buffer, format="png", dpi=RENDER_DPI, bbox_inches="tight", transparent=True)
    plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def style(fig, ax):
    """
    Apply the optional house figure treatment in place.

    Open top/right spines, a light dotted grid behind the data, muted ink and
    compact type, and a frameless legend — so an opted-in figure reads as part
    of the app rather than a stock matplotlib window.

    Parameters
    ----------
    fig: Figure
        The figure (accepted for signature symmetry with viz returns).
    ax: Axes
        The axes to restyle, already populated by the caller.
    """
    colors = theme.active()
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(colors.grid)
    ax.grid(True, axis="y", color=colors.grid, alpha=0.35, linewidth=0.6, linestyle=":")
    ax.set_axisbelow(True)
    ax.tick_params(colors=colors.ink, labelsize=9)
    ax.title.set_color(colors.ink)
    ax.title.set_fontsize(11)
    for label in (ax.xaxis.label, ax.yaxis.label):
        label.set_color(colors.ink)
        label.set_fontsize(10)
    legend = ax.get_legend()
    if legend is not None:
        legend.set_frame_on(False)
        for text in legend.get_texts():
            text.set_color(colors.ink)
            text.set_fontsize(9)
