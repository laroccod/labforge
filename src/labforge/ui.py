"""
Shared UI builders: the app's typographic and surface vocabulary.
"""

import flet as ft

from .mathtext import equation_image

# The app's two typographic voices: a grotesque for prose and a monospace for
# anything that is data — parameter labels, readouts, tables, telemetry lines.
# Both are bundled variable fonts (assets/fonts, registered in shell.build_main),
# so desktop, browser, Windows and Linux all render the same faces and weights
# rather than falling back to the platform default. FONT_ASSETS is the family ->
# asset-path map open() hands to Flet's asset server.
FONT_BODY = "Inter"
FONT_MONO = "Roboto Mono"
FONT_ASSETS = {FONT_BODY: "fonts/Inter.ttf", FONT_MONO: "fonts/RobotoMono.ttf"}

# The reading measure: every page constrains its content column to this width,
# so prose keeps a comfortable line length and control rows stay compact instead
# of stretching across the window. Chosen to fit the content pane at the
# shell's minimum window width.
MEASURE = 720


def image(data, width=None, height=None):
    """
    Display a raw base64 PNG (no data: prefix), as produced by figures/mathtext,
    at the given logical-pixel size (None keeps the intrinsic size).
    """
    # Flet 0.86 Image takes base64 directly on src (there is no src_base64).
    return ft.Image(src=data, width=width, height=height)


def fitted_image(data):
    """
    A figure image capped at the reading measure: an oversize figure scales
    down to fit (rendered at figures.RENDER_DPI it stays crisp on high-dpi
    displays), a smaller one keeps its intrinsic size, and either sits
    centered in its box.
    """
    return ft.Image(src=data, width=MEASURE, fit=ft.BoxFit.SCALE_DOWN)


def equation(latex, fontsize=18):
    """
    Render displayed math — content without surrounding dollar signs, e.g.
    r"f(x)=\\lambda" — as a LaTeX image sized to the measured equation.
    """
    img = equation_image(latex, fontsize=fontsize)
    return image(img["src"], width=img["width"], height=img["height"])


def heading(text):
    """Section heading: tracked display caps for the top of a page or section."""
    return ft.Text(
        text.upper(),
        style=ft.TextStyle(size=22, weight=ft.FontWeight.W_800, letter_spacing=1.5),
    )


def subheading(text):
    """Letterspaced all-caps microlabel that marks a block within a page."""
    return ft.Text(
        text.upper(),
        style=ft.TextStyle(
            size=11,
            weight=ft.FontWeight.W_700,
            letter_spacing=2.5,
            color=ft.Colors.PRIMARY,
            font_family=FONT_MONO,
        ),
    )


def mono(text, size=12, color=ft.Colors.ON_SURFACE_VARIANT):
    """
    Monospace telemetry text for status lines and small readouts.

    The colour rides on the Text, not its style, so a status line can flip to
    the error tone by assigning .color on the mounted control.
    """
    return ft.Text(
        text,
        color=color,
        style=ft.TextStyle(size=size, font_family=FONT_MONO, letter_spacing=0.5),
    )


def body(markdown):
    """Prose as selectable GitHub-flavored Markdown."""
    return ft.Markdown(
        value=markdown,
        selectable=True,
        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
    )


def action_button(label, on_click):
    """Primary action: a squared filled button with a tracked mono-caps label."""
    return ft.FilledButton(
        content=ft.Text(
            label.upper(),
            style=ft.TextStyle(
                size=13, weight=ft.FontWeight.W_700, letter_spacing=2, font_family=FONT_MONO
            ),
        ),
        on_click=on_click,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=2)),
    )


def card(content, padding=16):
    """
    Group related controls on a card surface: a lifted tone, a hairline outline
    and near-square corners.
    """
    return ft.Container(
        content=content,
        padding=padding,
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=2,
    )


def placeholder(text):
    """Muted card standing in for a section the author registered nothing for."""
    return card(ft.Text(text, color=ft.Colors.ON_SURFACE_VARIANT), padding=20)


def data_table(columns, rows):
    """
    An ft.DataTable (same columns/rows arguments) with the house treatment —
    tinted mono-caps heading row, hairline rules, monospace cells — so every
    table in an app reads the same.
    """
    return ft.DataTable(
        columns=columns,
        rows=rows,
        heading_row_color=ft.Colors.SURFACE_CONTAINER_LOW,
        heading_row_height=44,
        heading_text_style=ft.TextStyle(
            size=11,
            weight=ft.FontWeight.W_700,
            letter_spacing=2,
            font_family=FONT_MONO,
            color=ft.Colors.ON_SURFACE_VARIANT,
        ),
        data_text_style=ft.TextStyle(size=13, font_family=FONT_MONO),
        horizontal_lines=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=2,
        column_spacing=32,
    )


def centered(control):
    """Center a fixed-size control — an equation or figure image — in the measure."""
    return ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[control])


def fading_pane(content=None, duration=250, expand=False):
    """
    A pane that cross-fades whenever its content control is replaced.

    The house pattern for mutate-in-place swaps: the pane stays mounted and its
    .content is reassigned, so an open tab survives, but the change reads as a
    fade rather than a hard cut. Reassigning the same control instance is a
    no-op, so a repaint that produces the same control does not flash.
    """
    return ft.AnimatedSwitcher(
        content=content if content is not None else ft.Container(),
        duration=duration,
        reverse_duration=duration,
        transition=ft.AnimatedSwitcherTransition.FADE,
        expand=expand,
    )


def needs_run():
    """Instrument-panel status line shown before the worker has been run."""
    return card(
        ft.Row(
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(ft.Icons.SCIENCE_OUTLINED, size=18, color=ft.Colors.PRIMARY),
                ft.Text(
                    "NO DATA",
                    style=ft.TextStyle(
                        size=12,
                        weight=ft.FontWeight.W_700,
                        letter_spacing=2,
                        font_family=FONT_MONO,
                    ),
                ),
                mono("— set parameters on the Simulation page and press RUN"),
            ],
        ),
        padding=16,
    )


def page_scaffold(title, controls):
    """
    Scrollable page body: a heading above the supplied controls, in a column
    constrained to the reading measure that scrolls when tall.
    """
    return ft.Column(
        expand=True,
        width=MEASURE,
        scroll=ft.ScrollMode.AUTO,
        spacing=16,
        controls=[heading(title), *controls],
    )
