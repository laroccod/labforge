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
    than a blank pane. Before the worker has produced data, the output slot
    holds the run-gate card instead — the entry, its description and controls
    stay explorable, only the output waits.

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
    status = ui.mono("")
    # A fading pane, so the run gate dissolves into the output when data lands.
    # The gate card is built once: reassigning the same control is a no-op, so
    # an actionless refresh does not fade the gate into itself.
    gate = ui.needs_run()
    holder = ui.fading_pane()

    def refresh():
        if not state.has_data():
            holder.content = gate
            return
        holder.content = output
        kwargs = {name: binding.read() for name, binding in bindings.items()}
        # Hand the shared context to a viz/analysis that declares it, alongside
        # the worker data — the same injection the worker itself receives.
        if wants_context(entry.func):
            kwargs[CONTEXT_PARAM] = state.context
        try:
            show(entry.func(state.data, **kwargs))
            status.value = ""
            status.color = ft.Colors.ON_SURFACE_VARIANT
        except Exception as err:  # surface the author's failure, keep the app alive
            status.value = f"{entry.title} raised {type(err).__name__}: {err}"
            status.color = ft.Colors.ERROR

    def on_action(e=None):
        refresh()
        page.update()

    bindings = {
        name: build_control(name, param, values, page, on_submit=on_action)
        for name, param in entry.params.items()
    }

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
    return [*header, controls_card, holder]


def build(title, entries, state, page, section, empty):
    """
    Build a tabbed page — one tab per registered entry — or the placeholder
    scaffold when there is nothing to show. Each entry gates its own output
    slot on run state, so the tabs stay explorable before the first Run.

    Parameters
    ----------
    section: callable
        section(entry, state, page) -> list of controls for one entry.
    empty: str
        Placeholder text shown when nothing is registered.
    """
    if not entries:
        return ui.page_scaffold(title, [ui.placeholder(empty)])

    # Flet 0.86 Tabs is a controller wrapping a separate TabBar and TabBarView,
    # whose control count must equal length.
    tabs = ft.Tabs(
        length=len(entries),
        expand=True,
        content=ft.Column(
            expand=True,
            controls=[
                # Tab labels speak the same mono voice as every other label.
                ft.TabBar(
                    label_color=ft.Colors.PRIMARY,
                    unselected_label_color=ft.Colors.ON_SURFACE_VARIANT,
                    label_text_style=ft.TextStyle(
                        size=12,
                        weight=ft.FontWeight.W_700,
                        letter_spacing=1.5,
                        font_family=ui.FONT_MONO,
                    ),
                    unselected_label_text_style=ft.TextStyle(
                        size=12, letter_spacing=1.5, font_family=ui.FONT_MONO
                    ),
                    tabs=[ft.Tab(label=entry.title) for entry in entries],
                ),
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
    # ancestor heights, so each tab body scrolls on its own instead. Width is
    # the reading measure, matching page_scaffold.
    return ft.Column(expand=True, width=ui.MEASURE, spacing=16, controls=[ui.heading(title), tabs])
