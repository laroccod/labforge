"""
The app chrome: top bar, navigation rail or scroll layout, and the single
LabState every page shares.
"""

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

        # App mark: the lab's icon (a volume mark by default) on a sharp accent tile.
        app_mark = ft.Container(
            width=30,
            height=30,
            border_radius=2,
            bgcolor=ft.Colors.PRIMARY,
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(lab.icon or ft.Icons.VIEW_IN_AR, size=18, color=ft.Colors.ON_PRIMARY),
        )

        # Thin header strip: mark and tracked mono-caps title on the left, a
        # factual mono readout (the registered worker) on the right.
        top_bar = ft.Container(
            padding=ft.Padding.symmetric(horizontal=20, vertical=10),
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            app_mark,
                            ft.Text(
                                lab.title.upper(),
                                style=ft.TextStyle(
                                    size=14,
                                    weight=ft.FontWeight.W_700,
                                    letter_spacing=3,
                                    font_family=ui.FONT_MONO,
                                ),
                            ),
                        ],
                    ),
                    ft.Text(
                        f"WORKER · {lab.worker.func.__name__.upper()}",
                        style=ft.TextStyle(
                            size=11,
                            letter_spacing=2,
                            font_family=ui.FONT_MONO,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                    ),
                ],
            ),
        )

        if layout == "scroll":
            # One continuous page under the top bar; no rail, no navigation.
            body = ft.Container(expand=True, padding=24, content=scroll.build(state, page))
        else:
            # Right-hand pane; its single child is swapped on navigation.
            content = ft.Container(expand=True, padding=24)

            def show_page(index):
                # Rebuild-on-navigate: build fresh so the page re-reads LabState.
                content.content = PAGES[index][2](state, page)

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
