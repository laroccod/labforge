"""
Simulation page: the worker's controls, a Run action and a status line.
"""

import flet as ft

from .. import ui
from ..controls import build_control


def section(state, page, after_run=None):
    """
    Build the worker's intro prose and controls card as a stackable list.

    Parameters
    ----------
    after_run: callable
        Invoked after a successful run, before the page update — the scroll
        layout uses it to rebuild the visualization and analysis sections.
    """
    worker = state.lab.worker
    bindings = {
        name: build_control(name, param, state.worker_values, page)
        for name, param in worker.params.items()
    }
    # Flet 0.86 has no SnackBar, so status lives in the tree where page.update()
    # always reaches it.
    status = ui.mono(state.run_summary)

    def on_run(e):
        for name, binding in bindings.items():
            state.worker_values[name] = binding.read()
        try:
            # Synchronous in the handler: workers are expected fast. page.run_task
            # with a worker thread is the seam if long runs ever need a live UI.
            state.run()
            status.value = state.run_summary
            if after_run is not None:
                after_run()
        except Exception as err:  # surface the worker's failure, keep the app alive
            status.value = f"Worker raised {type(err).__name__}: {err}"
        page.update()

    scannable = [name for name, param in worker.params.items() if param.scan]
    scan_note = (
        f" Parameters marked scan ({', '.join(scannable)}) accept comma-separated "
        "values; the worker then runs once per point of the cartesian grid."
        if scannable
        else ""
    )
    intro = ui.body(
        f"Set the parameters of **{worker.func.__name__}** and press Run. "
        "The visualization and analysis sections read the most recent result." + scan_note
    )
    controls_card = ui.card(
        ft.Column(
            spacing=12,
            controls=[
                ui.subheading("Parameters"),
                *[binding.row for binding in bindings.values()],
                ui.action_button("Run", on_run),
                status,
            ],
        )
    )
    return [intro, controls_card]


def build(state, page):
    """Build the simulation page for the registered worker."""
    return ui.page_scaffold("Simulation", section(state, page))
