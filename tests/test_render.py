"""
Analysis dispatch tests

Coverage of pages/analysis.render_result, the one place an author's return type
picks its own treatment, plus the figure unpacking it shares with the viz page.
"""

import flet as ft
import matplotlib.pyplot as plt
import pytest

from labforge.figures import is_figure, unpack_figure
from labforge.pages.analysis import render_result


class FakeFrame:
    """Duck-typed stand-in for a DataFrame: render_result never imports pandas."""

    columns = ["mu", "mean"]

    def itertuples(self, index=False):
        return iter([(0.0, 0.1), (1.0, 1.2)])


def test_dict_becomes_a_two_column_table():
    table = render_result({"mean": 0.5, "std": 1.0})
    assert isinstance(table, ft.DataTable)
    assert [c.label.value for c in table.columns] == ["QUANTITY", "VALUE"]
    assert len(table.rows) == 2


def test_list_of_dicts_becomes_a_records_table():
    table = render_result([{"mu": 0.0, "mean": 0.1}, {"mu": 1.0, "mean": 1.2}])
    assert [c.label.value for c in table.columns] == ["MU", "MEAN"]
    assert len(table.rows) == 2


def test_dataframe_is_duck_typed_into_a_records_table():
    table = render_result(FakeFrame())
    assert [c.label.value for c in table.columns] == ["MU", "MEAN"]
    assert len(table.rows) == 2


def test_string_becomes_markdown():
    assert isinstance(render_result("**bold**"), ft.Markdown)


@pytest.mark.parametrize("as_tuple", [False, True])
def test_figure_becomes_an_image(as_tuple):
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    control = render_result((fig, ax) if as_tuple else fig)
    assert isinstance(control, ft.Image)
    assert control.src  # an empty src would mean the render silently failed


def test_unknown_return_falls_back_to_its_repr():
    control = render_result(42)
    assert isinstance(control, ft.Markdown)
    assert "42" in control.value


def test_float_cells_are_formatted_compactly():
    table = render_result({"mean": 0.123456789})
    assert table.rows[0].cells[1].content.value == "0.1235"


def test_is_figure_rejects_the_shapes_unpack_cannot_take():
    fig = plt.figure()
    assert is_figure(fig) and is_figure((fig, "ax"))
    assert not is_figure(()) and not is_figure(("ax", fig)) and not is_figure([fig])
    plt.close(fig)


def test_unpack_figure_names_what_it_got():
    with pytest.raises(TypeError, match="got str"):
        unpack_figure("not a figure")
