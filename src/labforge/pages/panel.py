"""
Shared machinery for the visualization and analysis pages, which differ only in
what they put on screen.
"""

import flet as ft

from .. import ui
from ..controls import build_control
from ..param import CONTEXT_PARAM, wants_context


def section_controls(entry, state, values, page, action, output, show):
    """
    Build one registered entry as a stackable list: the optional description,
    the controls card, and output.

    The output control is persistent: show() mutates it in place rather than
    replacing it, so the open tab survives a re-render. The first paint runs
    from the stored kwargs, so returning to a page shows finished output rather
    than a blank pane.

    Parameters
    ----------
    values: dict
        The entry's persisted {kwarg: value}; controls read and commit to it.
    action: str
        Action button label ("Render", "Compute").
    output: Control
        The persistent pane show() writes into.
    show: callable
        show(result) -> None, writing the entry function's return into output.
    """
    bindings = {
        name: build_control(name, param, values, page) for name, param in entry.params.items()
    }
    status = ui.mono("")

    def refresh():
        kwargs = {name: binding.read() for name, binding in bindings.items()}
        # Hand the shared context to a viz/analysis that declares it, alongside
        # the worker data — the same injection the worker itself receives.
        if wants_context(entry.func):
            kwargs[CONTEXT_PARAM] = state.context
        try:
            show(entry.func(state.data, **kwargs))
            status.value = ""
        except Exception as err:  # surface the author's failure, keep the app alive
            status.value = f"{entry.title} raised {type(err).__name__}: {err}"

    def on_action(e):
        refresh()
        page.update()

    refresh()  # first paint, from the kwargs the last visit left behind
    controls_card = ui.card(
        ft.Column(
            spacing=12,
            controls=[
                *[binding.row for binding in bindings.values()],
                ui.action_button(action, on_action),
                status,
            ],
        )
    )
    header = [ui.body(entry.desc)] if entry.desc else []
    return [*header, controls_card, output]


def build(title, entries, state, page, section, empty, gated=True):
    """
    Build a tabbed page — one tab per registered entry, behind the run gate —
    or the placeholder / run-gate scaffold when there is nothing to show.

    Parameters
    ----------
    section: callable
        section(entry, state, page) -> list of controls for one entry.
    empty: str
        Placeholder text shown when nothing is registered.
    gated: bool
        Show the run gate until data exists. The viz/analysis pages gate on the
        worker output they consume; the tabbed Simulation page passes False,
        since it is where the running happens.
    """
    if not entries:
        return ui.page_scaffold(title, [ui.placeholder(empty)])
    if gated and not state.has_data():
        return ui.page_scaffold(title, [ui.needs_run()])

    # Flet 0.86 Tabs is a controller wrapping a separate TabBar and TabBarView,
    # whose control count must equal length.
    tabs = ft.Tabs(
        length=len(entries),
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                ft.TabBar(tabs=[ft.Tab(label=entry.title) for entry in entries]),
                ft.TabBarView(
                    expand=True,
                    # Each tab body scrolls itself; see the column note below.
                    controls=[
                        ft.Column(
                            expand=True,
                            scroll=ft.ScrollMode.AUTO,
                            spacing=12,
                            controls=section(entry, state, page),
                        )
                        for entry in entries
                    ],
                ),
            ],
        ),
    )
    # Deliberately not a scrolling column: an expanding TabBarView needs bounded
    # ancestor heights, so each tab body scrolls on its own instead.
    return ft.Column(expand=True, spacing=16, controls=[ui.heading(title), tabs])
