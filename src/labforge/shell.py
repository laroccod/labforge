"""
The app chrome: top bar, navigation rail or scroll layout, and the single
LabState every page shares.
"""

import asyncio
import random

import flet as ft

from . import theme as themes
from . import ui
from .pages import analysis, scroll, simulation, theory, visualization
from .state import LabState

PAGES = [
    ("Theory", ft.Icons.MENU_BOOK, theory.build),
    ("Simulation", ft.Icons.TERMINAL, simulation.build),
    ("Visualization", ft.Icons.AUTO_GRAPH, visualization.build),
    ("Analysis", ft.Icons.TROUBLESHOOT, analysis.build),
]

LAYOUTS = ("pages", "scroll")


def color_scheme(theme):
    """
    Map a Theme onto the Flet ColorScheme slots the pages resolve through.

    Pages never name a hex; they style themselves with ft.Colors tokens, so this
    mapping is the only place the palette reaches the UI.
    """
    return ft.ColorScheme(
        primary=theme.accent,
        on_primary=theme.on_accent,
        primary_container=theme.accent_dim,
        on_primary_container=theme.on_accent_dim,
        secondary=theme.accent,
        on_secondary=theme.on_accent,
        secondary_container=theme.accent_dim,
        on_secondary_container=theme.on_accent_dim,
        surface=theme.surface,
        on_surface=theme.on_surface,
        on_surface_variant=theme.on_surface_variant,
        surface_container_lowest=theme.surface_lowest,
        surface_container_low=theme.surface_low,
        surface_container=theme.surface_container,
        surface_container_high=theme.surface_high,
        surface_container_highest=theme.surface_highest,
        outline=theme.outline,
        outline_variant=theme.outline_variant,
        surface_tint=theme.accent,
    )


def animated_wordmark(lab, page):
    """
    The app mark and title for the top bar. The mark is static; the title
    letters are individual tiles that blow apart when the pointer enters, float
    around for as long as it stays, and spring back into the wordmark the
    moment it leaves.

    Floating is a chain of implicit animations: every beat each letter is given
    a new random target, with the transition lasting exactly one beat, so a
    letter never comes to rest between targets. The float task runs via
    page.run_task so its updates reach the client (a bare thread's update is
    silently dropped); an epoch counter keeps a stale float loop from a
    previous hover writing over the current one.
    """
    blow = ft.Animation(500, ft.AnimationCurve.EASE_OUT_CUBIC)
    drift = ft.Animation(1200, ft.AnimationCurve.EASE_IN_OUT_SINE)
    spring = ft.Animation(400, ft.AnimationCurve.EASE_OUT_BACK)
    letters = [
        ft.Container(
            content=ft.Text(
                letter,
                style=ft.TextStyle(size=14, weight=ft.FontWeight.W_700, font_family=ui.FONT_MONO),
            ),
            offset=ft.Offset(0, 0),
            rotate=ft.Rotate(0),
            animate_offset=spring,
            animate_rotation=spring,
        )
        for letter in lab.title.upper()
    ]
    mark = ft.Container(
        width=30,
        height=30,
        border_radius=2,
        bgcolor=ft.Colors.PRIMARY,
        alignment=ft.Alignment.CENTER,
        content=ft.Icon(lab.icon or ft.Icons.VIEW_IN_AR, size=18, color=ft.Colors.ON_PRIMARY),
    )
    hover = {"on": False, "epoch": 0}

    def animate_with(animation):
        for letter in letters:
            letter.animate_offset = animation
            letter.animate_rotation = animation

    def scatter():
        # Offsets are fractions of the letter tile — a wide throw sideways, a
        # shallower one vertically, so the cloud stays inside the top bar.
        for letter in letters:
            letter.offset = ft.Offset(random.uniform(-1.5, 1.5), random.uniform(-0.6, 0.6))
            letter.rotate = ft.Rotate(random.uniform(-0.6, 0.6))

    def settle():
        animate_with(spring)
        for letter in letters:
            letter.offset = ft.Offset(0, 0)
            letter.rotate = ft.Rotate(0)

    async def float_around(epoch):
        # Blow apart fast, then drift: each beat hands every letter a new
        # target reached in exactly one beat, so the motion never pauses.
        animate_with(blow)
        scatter()
        page.update()
        await asyncio.sleep(0.5)
        animate_with(drift)
        while hover["on"] and hover["epoch"] == epoch:
            scatter()
            page.update()
            await asyncio.sleep(1.2)
        # Reset only if no newer hover has taken over the letters.
        if not hover["on"]:
            settle()
            page.update()

    def on_hover(e):
        # Flet 0.86 sends hover data as a boolean: True on enter, False on exit.
        entering = str(e.data).lower() == "true"
        hover["on"] = entering
        if entering:
            hover["epoch"] += 1
            page.run_task(float_around, hover["epoch"])
        else:
            settle()
            page.update()

    # Row spacing stands in for the wordmark's letterspacing, since each letter
    # now carries its own tile.
    return ft.Container(
        on_hover=on_hover,
        content=ft.Row(
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[mark, ft.Row(spacing=4, controls=letters)],
        ),
    )


def worker_selector(state):
    """
    The top bar's right-hand readout. Workers are switched on the Simulation page
    (tabs view) or by the Theory-page model selector (selects_worker), never in
    the top bar, so this is a plain, static readout of the active model or the
    worker count — never a control.
    """
    label = ft.Text(
        "WORKER",
        style=ft.TextStyle(
            size=11, letter_spacing=2, font_family=ui.FONT_MONO, color=ft.Colors.ON_SURFACE_VARIANT
        ),
    )

    def readout_row(text):
        return ft.Row(
            spacing=6,
            controls=[
                label,
                ft.Text(
                    text,
                    style=ft.TextStyle(
                        size=11,
                        letter_spacing=2,
                        font_family=ui.FONT_MONO,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ),
            ],
        )

    # In tabs view the workers are Simulation-page tabs; a plain count stands in.
    if state.tabbed:
        return readout_row(f"· {len(state.lab.workers)} TABS")
    # A model selector switches the worker from the Theory page; a static count
    # stands in (the active model would go stale — the top bar is not rebuilt
    # when the selection changes).
    if state.lab.selects_worker:
        return readout_row(f"· {len(state.lab.workers)} MODELS")
    # Otherwise a single-worker lab: name the one worker.
    return readout_row(f"· {state.active.upper()}")


def build_main(lab, layout="pages", theme=themes.DEFAULT):
    """
    Return the Flet entry point — a main(page) callable — for a Lab.

    Parameters
    ----------
    lab: Lab
        The validated registrations and branding.
    layout: str
        "pages" for the rail-navigated four-page shell, "scroll" for one
        continuous scrolling page.
    theme: str
        A key of theme.THEMES. Selected here, once, before the app serves —
        figures and equations read it back through theme.active().

    Returns
    -------
    A main(page) callable; also the headless seam the page-tree tests drive.
    """
    if layout not in LAYOUTS:
        raise ValueError(f"layout must be one of {sorted(LAYOUTS)}, got {layout!r}.")

    palette = themes.use(theme)
    scheme = color_scheme(palette)

    # Flet calls main(page) once per connection, so every browser tab that opens
    # the served app gets its own LabState. Nothing may be cached out here
    # except immutable config.
    def main(page):
        page.title = lab.page_title
        # Register the bundled variable fonts (served from assets_dir, set in
        # open()); both carry a wght axis so ft.FontWeight resolves to real
        # weights, not synthetic bold.
        page.fonts = dict(ui.FONT_ASSETS)
        # The mode matches the palette so widget defaults the scheme does not
        # name (shadows, ripples, error tones) derive with the right brightness.
        page.theme_mode = ft.ThemeMode.DARK if palette.mode == "dark" else ft.ThemeMode.LIGHT
        # The seed fills the scheme slots color_scheme leaves unset; the same
        # Theme is set on both slots so the explicit surfaces win regardless of
        # which one Flet consults for the mode.
        page_theme = ft.Theme(
            color_scheme_seed=palette.accent, color_scheme=scheme, font_family=ui.FONT_BODY
        )
        page.theme = page_theme
        page.dark_theme = page_theme
        page.window.width = 1120
        page.window.height = 840
        page.window.min_width = 900
        page.window.min_height = 640

        # The one state object every page reads from and writes to.
        state = LabState(lab)

        # Layout builds the body. Worker switching happens inside the pages
        # (Simulation tabs, or the Theory model selector), so the top bar needs
        # no rebuild hook.
        # The explicit alignment loosens the pane's constraints, so a page
        # column's reading-measure width holds instead of being stretched to
        # the pane.
        if layout == "scroll":
            # One continuous page under the top bar; no rail, no navigation.
            body = ft.Container(
                expand=True,
                padding=24,
                alignment=ft.Alignment.TOP_LEFT,
                content=scroll.build(state, page),
            )
        else:
            # Right-hand pane; its single child is swapped on navigation, and
            # the switcher cross-fades the outgoing page into the incoming one.
            switcher = ui.fading_pane(duration=70, expand=True)
            content = ft.Container(
                expand=True, padding=24, alignment=ft.Alignment.TOP_LEFT, content=switcher
            )

            def show_page(index):
                # Rebuild-on-navigate: build fresh so the page re-reads LabState.
                switcher.content = PAGES[index][2](state, page)

            def on_nav_change(e):
                show_page(e.control.selected_index)
                page.update()

            # Spec-sheet rail: numbered mono-caps labels, a squared indicator.
            rail = ft.NavigationRail(
                selected_index=0,
                label_type=ft.NavigationRailLabelType.ALL,
                min_width=100,
                bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST,
                indicator_color=ft.Colors.PRIMARY_CONTAINER,
                indicator_shape=ft.RoundedRectangleBorder(radius=2),
                selected_label_text_style=ft.TextStyle(
                    size=11,
                    weight=ft.FontWeight.W_700,
                    letter_spacing=1.5,
                    font_family=ui.FONT_MONO,
                    color=ft.Colors.PRIMARY,
                ),
                unselected_label_text_style=ft.TextStyle(
                    size=11,
                    letter_spacing=1.5,
                    font_family=ui.FONT_MONO,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                on_change=on_nav_change,
                destinations=[
                    ft.NavigationRailDestination(
                        icon=icon, label=f"{index + 1:02d} {label.upper()}"
                    )
                    for index, (label, icon, _) in enumerate(PAGES)
                ],
            )

            # Render the first page before mounting, so no handler fires against
            # an unattached tree.
            show_page(0)

            body = ft.Row(
                expand=True,
                controls=[
                    rail,
                    ft.VerticalDivider(width=1, color=ft.Colors.OUTLINE_VARIANT),
                    content,
                ],
            )

        # Thin header strip: mark and tracked mono-caps title on the left; on the
        # right a factual worker readout, or a selector when the lab has several.
        worker_readout = worker_selector(state)
        top_bar = ft.Container(
            padding=ft.Padding.symmetric(horizontal=20, vertical=10),
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    animated_wordmark(lab, page),
                    worker_readout,
                ],
            ),
        )

        page.add(
            ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    top_bar,
                    ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
                    body,
                ],
            )
        )

    return main
