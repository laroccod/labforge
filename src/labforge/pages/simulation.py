"""
Simulation page: the worker's controls, a Run action and a status line.
"""

import asyncio
import time
from collections import namedtuple

import flet as ft

from .. import ui
from ..controls import build_control
from . import panel

# A Simulation tab stands in for one worker; panel.build labels tabs by .title.
WorkerTab = namedtuple("WorkerTab", "title")

EMPTY = "No workers registered — add one with Lab.add_worker."


def section(state, page, after_run=None, worker_name=None):
    """
    Build one worker's intro prose and controls card as a stackable list.

    Parameters
    ----------
    after_run: callable
        Invoked after a successful run, before the page update — the scroll
        layout uses it to rebuild the visualization and analysis sections.
    worker_name: str
        The worker to build for; the active worker when omitted. The tabbed
        Simulation page passes each worker's name so all tabs stay live at once.
    """
    name = worker_name or state.active
    worker = state.lab.workers[name]
    values = state.workspaces[name].worker_values
    bindings = {
        param_name: build_control(
            param_name, param, values, page, on_submit=lambda: page.run_task(perform_run)
        )
        for param_name, param in worker.params.items()
    }
    # Flet 0.86 has no SnackBar, so status lives in the tree where page.update()
    # always reaches it. The opacity animation carries the RUNNING pulse.
    status = ui.mono(state.workspaces[name].run_summary)
    status.animate_opacity = ft.Animation(600, ft.AnimationCurve.EASE_IN_OUT)
    run_button = ui.action_button("Run", lambda e: page.run_task(perform_run))

    async def perform_run():
        # Run as a run_task coroutine so page.update() reaches the client (a bare
        # thread's update is silently dropped), and push the worker compute — the
        # slow part — to an executor so the event loop stays live and shows the
        # RUNNING line. Figure rendering in after_run stays on this loop thread,
        # keeping pyplot's global state touched by one thread only.
        loop = asyncio.get_running_loop()
        last_paint = {"t": 0.0}

        def report(done, total):
            # Called from the executor thread after each grid point: repaint on
            # the loop (a bare thread's update is dropped), throttled so a fast
            # scan does not flood the client with frames.
            now = time.monotonic()
            if done < total and now - last_paint["t"] < 0.1:
                return
            last_paint["t"] = now

            def paint():
                status.value = f"RUNNING · {done}/{total}"
                page.update()

            loop.call_soon_threadsafe(paint)

        async def pulse():
            # Breathe the status line while the run is in flight; the fade
            # length matches the beat, so the pulse is continuous. The loop
            # keys off the disabled Run button and restores full opacity on
            # its way out.
            while run_button.disabled:
                status.opacity = 0.35 if (status.opacity or 1) == 1 else 1
                page.update()
                await asyncio.sleep(0.6)
            status.opacity = 1
            page.update()

        for param_name, binding in bindings.items():
            values[param_name] = binding.read()
        run_button.disabled = True
        status.value = "RUNNING…"
        status.color = ft.Colors.ON_SURFACE_VARIANT
        status.opacity = 1
        asyncio.create_task(pulse())
        page.update()
        try:
            await loop.run_in_executor(None, lambda: state.run(name, progress=report))
            status.value = state.workspaces[name].run_summary
            if after_run is not None:
                after_run()
        except Exception as err:  # surface the worker's failure, keep the app alive
            status.value = f"Worker raised {type(err).__name__}: {err}"
            status.color = ft.Colors.ERROR
        finally:
            run_button.disabled = False
        page.update()

    scannable = [param_name for param_name, param in worker.params.items() if param.scan]
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
                run_button,
                status,
            ],
        )
    )
    return [intro, controls_card]


def build(state, page):
    """Build the Simulation page: one worker, workers as tabs, or the active tab.

    Tabs view lays every worker out as a tab. A model-selector lab shows only
    the active worker, but still as a single tab so the page matches the tabbed
    Visualization and Analysis pages. A plain single-worker lab keeps the bare
    controls with no tab bar.
    """
    if state.tabbed:
        return build_tabbed(state, page, list(state.lab.workers))
    if state.lab.selects_worker:
        return build_tabbed(state, page, [state.active])
    return ui.page_scaffold("Simulation", section(state, page))


def build_tabbed(state, page, names):
    """
    Build the named workers as tabs, one control set per worker, against one
    shared context. Reuses panel.build, the viz/analysis tabbed builder; the
    run gate lives in the output slots those pages add, so worker tabs carry
    none.
    """
    entries = [WorkerTab(title=name) for name in names]

    def worker_section(entry, state, page):
        return section(state, page, worker_name=entry.title)

    return panel.build("Simulation", entries, state, page, worker_section, EMPTY)
