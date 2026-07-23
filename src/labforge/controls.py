"""
Param -> a Flet control row plus a read() closure for its current value.
"""

from dataclasses import dataclass

import flet as ft

from .ui import FONT_MONO, fading_pane

# Parameter names and values are data, so every label, readout and field in a
# control row speaks the app's monospace voice.
MONO = ft.TextStyle(size=13, font_family=FONT_MONO)
MONO_LABEL = ft.TextStyle(size=12, font_family=FONT_MONO)

# Shared width of the leading label cell, so the control rows of a card align
# into a clean two-column grid.
LABEL_WIDTH = 120


@dataclass
class ControlBinding:
    """
    One built control row and its value accessor.

    Parameters
    ----------
    row: Control
        The labelled row to place in the page tree.
    read: callable
        Zero-arg closure returning the current parsed value (scalar, tuple,
        or list of scan values).
    """

    row: object
    read: callable


def build_control(name, param, values, page, on_change=None, on_submit=None):
    """
    Build the control row for one Param.

    Every control commits to values as it changes, so edits survive navigation
    even before the next Run; read() is also what Run, Render and Compute pull.

    Parameters
    ----------
    name: str
        The kwarg name; keys the values dict and labels the row by default.
    param: Param
        The normalized spec (default resolved, step filled for bounded kinds).
    values: dict
        The live values dict (state.worker_values or a per-tab kwargs dict);
        read at build time and committed to on every change.
    page: ft.Page
        Needed to flush live readout and parse-error updates.
    on_change: callable
        Optional callback(value) fired after a choice commits — the Theory-page
        selector uses it to rebuild the markdown its selection drives. Ignored
        by every other kind.
    on_submit: callable
        Optional zero-arg callback fired when Enter is pressed in a text
        field; the section builders pass their Run/Render/Compute action so a
        keyboard edit can commit and run in one stroke.

    Returns
    -------
    ControlBinding for the row.
    """
    label = param.label or name
    value = values.get(name, param.default)
    if param.kind == "choice":
        return choice_control(name, label, param, value, values, on_change)
    if param.kind == "tuple":
        return tuple_control(name, label, param, value, values, page, on_submit)
    if param.bounds is None and not param.scan:
        return text_control(name, label, param, value, values, page, on_submit)
    if param.bounds is None:
        return scan_control(name, label, param, value, values, page, on_submit)
    if not param.scan:
        return slider_control(name, label, param, value, values, page)
    return toggled_control(name, label, param, value, values, page, on_submit)


def label_cell(label, param):
    """The fixed-width row label; carries the param's help as a tooltip."""
    return ft.Text(label, width=LABEL_WIDTH, style=MONO, tooltip=param.help)


def label_row(label, param, body):
    """The uniform control row: a label cell, then the control body."""
    return ft.Row(
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[label_cell(label, param), body],
    )


def text_field(value, width, on_submit=None, hint=None):
    """A text field in the house style: hairline outline, near-square corners."""
    field = ft.TextField(
        value=value,
        width=width,
        text_style=MONO,
        border_color=ft.Colors.OUTLINE_VARIANT,
        border_radius=2,
        hint_text=hint,
    )
    if on_submit is not None:
        field.on_submit = lambda e: on_submit()
    return field


def slider_control(name, label, param, value, values, page, labelled=True):
    """A bounded param: a slider with a live readout."""
    lo, hi = param.bounds
    if isinstance(value, list):  # scan values left over from a stale spec edit
        value = param.default
    # Built here and returned inside the tree, so it is mounted before any drag
    # fires; on_change mutates it and flushes via page.update(), never
    # readout.update(), which Flet 0.86 drops.
    readout = ft.Text(format_scalar(param, value), width=64, style=MONO)
    slider = ft.Slider(
        min=lo,
        max=hi,
        divisions=max(1, round((hi - lo) / param.step)),
        value=value,
        label="{value}",
    )

    def on_change(e):
        readout.value = format_scalar(param, cast(param, e.control.value))
        page.update()

    def on_commit(e):
        values[name] = cast(param, e.control.value)

    slider.on_change = on_change
    slider.on_change_end = on_commit  # commit on release, not on every frame

    def read():
        return cast(param, slider.value)

    # The bare body is what toggled_control swaps in and out of its holder,
    # which keeps the label cell fixed while the control behind it changes.
    body = ft.Row(
        expand=True,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[ft.Container(slider, expand=True), readout],
    )
    row = label_row(label, param, body) if labelled else body
    return ControlBinding(row=row, read=read)


def text_control(name, label, param, value, values, page, on_submit):
    """An unbounded scalar or int: a validated text field."""
    field = text_field(format_scalar(param, value), 160, on_submit)

    def read():
        fallback = values.get(name, param.default)
        parsed, ok = parse_scalar(param, field.value, fallback)
        field.error = None if ok else f"invalid, kept {format_scalar(param, fallback)}"
        values[name] = parsed
        return parsed

    def on_change(e):
        read()
        page.update()  # paint or clear the parse-error flag as the user types

    field.on_change = on_change
    return ControlBinding(row=label_row(label, param, field), read=read)


def scan_control(name, label, param, value, values, page, on_submit):
    """An unbounded scan param: always a comma-separated values field."""
    field = text_field(format_values(param, value), 260, on_submit, hint="comma-separated to scan")

    def read():
        fallback = values.get(name, param.default)
        parsed, ok = parse_values(param, field.value, fallback)
        field.error = None if ok else f"invalid, kept {format_values(param, fallback)}"
        values[name] = parsed
        return parsed

    def on_change(e):
        read()
        page.update()

    field.on_change = on_change
    return ControlBinding(row=label_row(label, param, field), read=read)


def toggled_control(name, label, param, value, values, page, on_submit):
    """
    A bounded scan param: a slider row with a scan Switch.

    The switch swaps the content of a mounted fading pane between the slider
    and a comma-list field — the same mutate-in-place pattern the pages use for
    their result panes, so the mode change fades instead of cutting. Starting
    from a list value (a scan committed earlier) restores scan mode.
    """
    scanning = isinstance(value, list)
    slider_binding = slider_control(
        name, label, param, value if not scanning else param.default, values, page, labelled=False
    )
    field = text_field(format_values(param, value), 220, on_submit, hint="comma-separated to scan")
    # The switcher centers a lone child, so the field rides in a left-aligning
    # box to line up with the other rows' controls.
    field_box = ft.Container(content=field, alignment=ft.Alignment.CENTER_LEFT)
    holder = fading_pane(field_box if scanning else slider_binding.row, duration=200, expand=True)
    switch = ft.Switch(label="SCAN", value=scanning, label_position=ft.LabelPosition.RIGHT)

    def read():
        if switch.value:
            fallback = values.get(name, param.default)
            parsed, ok = parse_values(param, field.value, fallback)
            field.error = None if ok else f"invalid, kept {format_values(param, fallback)}"
        else:
            parsed = slider_binding.read()
        values[name] = parsed
        return parsed

    def on_toggle(e):
        if switch.value:
            # Carry the slider's value across, so switching to scan starts there.
            field.value = format_values(param, slider_binding.read())
            holder.content = field_box
        else:
            holder.content = slider_binding.row
        read()
        page.update()

    def on_field_change(e):
        read()
        page.update()

    switch.on_change = on_toggle
    field.on_change = on_field_change
    row = ft.Row(
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[label_cell(label, param), holder, switch],
    )
    return ControlBinding(row=row, read=read)


def tuple_control(name, label, param, value, values, page, on_submit):
    """A fixed-size tuple: one small text field per element."""
    fields = [text_field(f"{element:g}", 90, on_submit) for element in tuple(value)]
    for field in fields:
        field.text_align = ft.TextAlign.RIGHT

    def read():
        previous = tuple(values.get(name, param.default))
        parsed = []
        for field, element in zip(fields, previous):
            element_value, ok = parse_scalar(param, field.value, element)
            field.error = None if ok else f"kept {element:g}"
            parsed.append(element_value)
        values[name] = tuple(parsed)
        return values[name]

    def on_change(e):
        read()
        page.update()

    for field in fields:
        field.on_change = on_change
    body = ft.Row(vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=fields)
    return ControlBinding(row=label_row(label, param, body), read=read)


def choice_control(name, label, param, value, values, on_change):
    """
    A choice param: a Dropdown over the option strings.

    Commits the selected string to values like any other control. When on_change
    is given it fires after the commit with the new value, so a page can react to
    the selection (the Theory selector rebuilds its markdown this way).
    """
    if value not in param.options:  # a stale value from an edited spec
        value = param.default
    dropdown = ft.Dropdown(
        label=label,
        value=value,
        options=[ft.DropdownOption(key=option, text=option) for option in param.options],
        dense=True,
        text_style=MONO,
        label_style=MONO_LABEL,
        border_color=ft.Colors.OUTLINE_VARIANT,
        border_radius=2,
        width=260,
        tooltip=param.help,
    )

    def read():
        values[name] = dropdown.value
        return dropdown.value

    def on_select(e):
        read()
        if on_change is not None:
            on_change(dropdown.value)

    dropdown.on_select = on_select
    return ControlBinding(row=dropdown, read=read)


def cast(param, value):
    """
    Cast a slider value or one token of user text to the param's kind, rounding
    to the nearest int; raises on unparseable text.

    A tuple param's elements are floats, so they take the non-int branch.
    """
    return int(round(float(value))) if param.kind == "int" else float(value)


def format_scalar(param, value):
    """Display form of one value: thousands-grouped ints, compact floats."""
    return f"{int(value):,}" if param.kind == "int" else f"{float(value):g}"


def format_values(param, value):
    """
    Display form of a committed value or scan list for a comma field.

    Ints are ungrouped here, unlike format_scalar: a thousands separator inside
    a comma-separated list would parse back as two values.
    """
    entries = value if isinstance(value, list) else [value]
    return ", ".join(f"{int(v):d}" if param.kind == "int" else f"{float(v):g}" for v in entries)


def parse_scalar(param, text, fallback):
    """
    Parse one value of the param's kind into (value, ok).

    Bad input keeps the fallback with ok False, so the caller can hold the last
    good value live while flagging the field.
    """
    try:
        return cast(param, text), True
    except (TypeError, ValueError):
        return fallback, False


def parse_values(param, text, fallback):
    """
    Parse a comma-separated scan entry into (value, ok).

    A single valid value parses to a scalar (a one-point scan is just a run)
    and several to a list; any bad token, or no token at all, keeps the
    fallback with ok False.
    """
    parsed = []
    for token in str(text).split(","):
        token = token.strip()
        if not token:
            continue
        try:
            parsed.append(cast(param, token))
        except ValueError:
            return fallback, False
    if not parsed:
        return fallback, False
    return (parsed[0] if len(parsed) == 1 else parsed), True
