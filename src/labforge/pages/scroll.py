"""
Scroll layout: the whole lab as one continuous page, refreshed in place by Run.
"""

import flet as ft

from .. import ui
from . import analysis, simulation, theory, visualization


def divider():
    """Hairline rule between sections."""
    return ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT)


def results_content(state, page):
    """The visualization and analysis sections, or the run gate before data."""
    if not state.has_data():
        return ft.Column(spacing=16, controls=[ui.heading("Results"), ui.needs_run()])

    # Both kinds stack the same way; only the section builder differs.
    sections = [(entry, visualization.section_controls) for entry in state.lab.vizzes]
    sections += [(entry, analysis.section_controls) for entry in state.lab.analyses]
    controls = []
    for entry, section in sections:
        controls += [ui.heading(entry.title), *section(entry, state, page), divider()]
    if controls:
        controls.pop()  # no rule after the last section
    return ft.Column(spacing=16, controls=controls)


def build(state, page):
    """
    Build the single-page layout for the whole lab.

    With no navigation there is no rebuild-on-navigate to refresh downstream
    sections, so Run gets an after_run hook that rebuilds the mounted results
    container in place; the handler's page.update() then paints it in one flush.
    Tabs are avoided deliberately: an expanding TabBarView needs bounded
    ancestor heights, which a scrolling column cannot provide.
    """
    results = ft.Container()

    def refresh():
        results.content = results_content(state, page)

    refresh()
    return ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        spacing=16,
        controls=[
            ui.heading("Theory"),
            *theory.content(state),
            divider(),
            ui.heading("Simulation"),
            *simulation.section(state, page, after_run=refresh),
            divider(),
            results,
        ],
    )
