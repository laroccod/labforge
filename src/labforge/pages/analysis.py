"""
Analysis page: one tab per registered analysis, with a dispatched result pane.
"""

import flet as ft

from .. import ui
from ..figures import figure_to_base64, is_figure, unpack_figure
from . import panel

EMPTY = "No analyses registered — add one with Lab.add_analysis."


def section_controls(entry, state, page):
    """
    One analysis's description, kwarg controls, Compute action and result pane,
    as a list of controls. Shared by the tabbed page and the scroll layout.
    """
    pane = ft.Container()

    def show(value):
        # Swap only the content: the mounted Container stays, so the tab survives.
        pane.content = render_result(value)

    return panel.section_controls(
        entry, state, state.analysis_values[entry.title], page, "Compute", pane, show
    )


def build(state, page):
    """Build the tabbed analysis page."""
    return panel.build("Analysis", state.analyses, state, page, section_controls, EMPTY)


def render_result(value):
    """
    Dispatch an analysis return to a display control.

    What an analysis may return is deliberately loose: the author writes plain
    Python and the shape of the return picks the treatment.

    Parameters
    ----------
    value: object
        dict, list of dicts, DataFrame-like, str, Figure or (fig, ax), or
        anything with a repr as the fallback.

    Returns
    -------
    A Flet control rendering the value.
    """
    if isinstance(value, dict):
        return two_column_table(value)
    if isinstance(value, list) and value and all(isinstance(row, dict) for row in value):
        return records_table(value)
    if hasattr(value, "columns") and hasattr(value, "itertuples"):  # DataFrame, duck-typed
        return records_table(
            [dict(zip(value.columns, row)) for row in value.itertuples(index=False)]
        )
    if isinstance(value, str):
        return ui.body(value)
    if is_figure(value):
        return ui.image(figure_to_base64(unpack_figure(value)))
    return ui.body(f"`{value!r}`")


def format_cell(value):
    """Compact display form of one table cell."""
    return f"{value:.4g}" if isinstance(value, float) else str(value)


def two_column_table(mapping):
    """A {quantity: value} dict as a two-column table."""
    return ui.data_table(
        columns=[
            ft.DataColumn(ft.Text("QUANTITY")),
            ft.DataColumn(ft.Text("VALUE"), numeric=True),
        ],
        rows=[
            ft.DataRow(
                cells=[ft.DataCell(ft.Text(str(key))), ft.DataCell(ft.Text(format_cell(value)))]
            )
            for key, value in mapping.items()
        ],
    )


def records_table(records):
    """A list of homogeneous dicts as a table, columns taken from the first record."""
    columns = list(records[0])
    return ui.data_table(
        columns=[ft.DataColumn(ft.Text(str(name).upper())) for name in columns],
        rows=[
            ft.DataRow(
                cells=[ft.DataCell(ft.Text(format_cell(record.get(name)))) for name in columns]
            )
            for record in records
        ],
    )
