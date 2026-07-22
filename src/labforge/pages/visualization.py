"""
Visualization page: one tab per registered viz, each rendering a figure.
"""

from .. import ui
from ..figures import figure_to_base64, unpack_figure
from . import panel

EMPTY = "No visualizations registered — add one with Lab.add_viz."


def section_controls(entry, state, page):
    """
    One viz's description, kwarg controls, Render action and figure, as a list
    of controls. Shared by the tabbed page and the scroll layout.
    """
    image = ui.image("")

    def show(value):
        # Swap only the src: the mounted Image stays, so the open tab survives.
        image.src = figure_to_base64(unpack_figure(value))

    return panel.section_controls(
        entry, state, state.viz_values[entry.title], page, "Render", image, show
    )


def build(state, page):
    """Build the tabbed visualization page."""
    return panel.build("Visualization", state.vizzes, state, page, section_controls, EMPTY)
