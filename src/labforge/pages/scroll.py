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
    sections = [(entry, visualization.section_controls) for entry in state.vizzes]
    sections += [(entry, analysis.section_controls) for entry in state.analyses]
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
    sim_box = ft.Container()

    def refresh():
        results.content = results_content(state, page)

    def rebuild_sim():
        sim_box.content = ft.Column(spacing=16, controls=simulation_sections(state, page, refresh))

    # A model-switching Theory selector changes the active worker, so both the
    # Simulation controls and the results must rebuild for the new model.
    def on_model_change():
        rebuild_sim()
        refresh()

    rebuild_sim()
    refresh()
    return ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        spacing=16,
        controls=[
            ui.heading("Theory"),
            *theory.section(state, page, on_model_change=on_model_change),
            divider(),
            ui.heading("Simulation"),
            sim_box,
            divider(),
            results,
        ],
    )


def simulation_sections(state, page, refresh):
    """
    The Simulation controls for the scroll layout.

    One worker's section normally; in tabs view the scroll layout cannot host
    tabs, so every worker is stacked under its own subheading instead.
    """
    if not state.tabbed:
        return simulation.section(state, page, after_run=refresh)
    controls = []
    for name in state.lab.workers:
        controls.append(ui.subheading(name))
        controls += simulation.section(state, page, after_run=refresh, worker_name=name)
    return controls
