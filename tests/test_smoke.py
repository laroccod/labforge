"""
UI smoke tests

Construct every page's control tree without a running window, driving labforge
with the stub lab. This dodges the CanvasKit blank-canvas gap (web renders
blank in a sandboxed browser) while still catching import errors, wrong Flet
0.86 API usage, and empty equation/plot images.
"""

import flet as ft

from labforge.pages import analysis, scroll, simulation, theory, visualization
from labforge.state import LabState

from stubs import FakePage, ShellFakePage, collect_images, find_first, make_lab


def fresh_state():
    return LabState(make_lab())


def test_shell_wires_four_destinations():
    state_page = ShellFakePage()
    make_lab().build_main()(state_page)
    rail = find_first(state_page.controls[0], lambda c: isinstance(c, ft.NavigationRail))
    assert rail is not None
    assert [d.label for d in rail.destinations] == [
        "01 THEORY",
        "02 SIMULATION",
        "03 VISUALIZATION",
        "04 ANALYSIS",
    ]


def test_theory_page_interleaves_equations():
    tree = theory.build(fresh_state(), FakePage())
    images = collect_images(tree)
    assert len(images) == 1  # the one $$...$$ block in the stub theory
    assert all(images)  # a failed render would leave an empty src


def test_multiline_equation_blocks_collapse_to_one_line(monkeypatch):
    # matplotlib renders each line of a multi-line string separately, and a
    # line with an unmatched $ renders as literal text — so the equation must
    # reach ui.equation with its newlines collapsed.
    captured = []
    monkeypatch.setattr(
        theory.ui, "equation", lambda latex, fontsize=18: captured.append(latex) or ft.Text("eq")
    )
    state = fresh_state()
    state.lab.theory_source = "prose\n\n$$a = b \\\\\n+ c$$\n\nmore prose"
    theory.build(state, FakePage())
    assert captured == ["a = b \\\\ + c"]


def test_all_pages_build_before_any_run():
    state = fresh_state()
    page = FakePage()
    for build in (theory.build, simulation.build, visualization.build, analysis.build):
        assert build(state, page) is not None
    # Viz and Analysis show the run gate, not tabs, before the first run.
    gate = find_first(
        visualization.build(state, page),
        lambda c: isinstance(c, ft.Text) and c.value == "NO DATA",
    )
    assert gate is not None


def test_pages_build_after_scalar_run():
    state = fresh_state()
    page = FakePage()
    state.run()
    assert state.n_points == 1

    viz_tree = visualization.build(state, page)
    images = [src for src in collect_images(viz_tree) if src]
    assert images  # the histogram rendered on build from stored kwargs

    analysis_tree = analysis.build(state, page)
    table = find_first(analysis_tree, lambda c: isinstance(c, ft.DataTable))
    assert table is not None
    assert len(table.columns) == 2  # dict result -> Quantity/Value table


def test_pages_build_after_scan_run():
    state = fresh_state()
    page = FakePage()
    state.worker_values["mu"] = [0.0, 1.0]
    state.worker_values["sigma"] = [0.5, 1.0, 2.0]
    state.run()
    assert state.n_points == 6

    images = [src for src in collect_images(visualization.build(state, page)) if src]
    assert images

    table = find_first(analysis.build(state, page), lambda c: isinstance(c, ft.DataTable))
    assert table is not None
    assert len(table.rows) == 6  # one record per grid point


def test_simulation_run_handler_fills_status():
    state = fresh_state()
    tree = simulation.build(state, FakePage())
    button = find_first(tree, lambda c: isinstance(c, ft.FilledButton))
    button.on_click(None)
    assert state.has_data()
    status = find_first(
        tree, lambda c: isinstance(c, ft.Text) and "RUN COMPLETE" in (c.value or "")
    )
    assert status is not None


def test_scroll_layout_builds_and_gates():
    state = fresh_state()
    tree = scroll.build(state, FakePage())
    # theory equation renders; viz/analysis sit behind the run gate
    assert [src for src in collect_images(tree) if src]
    gate = find_first(tree, lambda c: isinstance(c, ft.Text) and c.value == "NO DATA")
    assert gate is not None
    rail = find_first(tree, lambda c: isinstance(c, ft.NavigationRail))
    assert rail is None


def test_scroll_layout_run_refreshes_results_in_place():
    state = fresh_state()
    tree = scroll.build(state, FakePage())
    # before the run, the only FilledButton in the tree is Run (the gate hides
    # the viz/analysis sections and their Render/Compute buttons)
    button = find_first(tree, lambda c: isinstance(c, ft.FilledButton))
    button.on_click(None)
    assert state.has_data()
    # after_run rebuilt the results container inside the same tree: the gate is
    # gone, the histogram image and the moments table are present
    gate = find_first(tree, lambda c: isinstance(c, ft.Text) and c.value == "NO DATA")
    assert gate is None
    assert len([src for src in collect_images(tree) if src]) >= 2  # equation + figure
    assert find_first(tree, lambda c: isinstance(c, ft.DataTable)) is not None


def test_shell_scroll_layout_has_no_rail():
    import pytest

    state_page = ShellFakePage()
    make_lab().build_main(layout="scroll")(state_page)
    rail = find_first(state_page.controls[0], lambda c: isinstance(c, ft.NavigationRail))
    assert rail is None
    with pytest.raises(ValueError, match="layout must be"):
        make_lab().build_main(layout="ribbon")


def test_every_theme_builds_the_shell():
    import pytest

    from labforge import theme as theme_module

    try:
        for name in theme_module.THEMES:
            state_page = ShellFakePage()
            make_lab().build_main(theme=name)(state_page)
            scheme = state_page.theme.color_scheme
            assert scheme.primary == theme_module.THEMES[name].accent
            # The equation ink follows the theme, so a page still renders under it.
            images = collect_images(theory.build(LabState(make_lab()), FakePage()))
            assert all(images)
        with pytest.raises(ValueError, match="theme must be"):
            make_lab().build_main(theme="gruvbox")
    finally:
        # The active theme is process-wide; leave the default for other tests.
        theme_module.use(theme_module.DEFAULT)


def test_worker_exception_is_surfaced_not_raised():
    from labforge import Lab

    def broken(x=1.0):
        raise RuntimeError("boom")

    lab = Lab("brokenlab")
    lab.add_worker(broken)
    state = LabState(lab)
    tree = simulation.build(state, FakePage())
    button = find_first(tree, lambda c: isinstance(c, ft.FilledButton))
    button.on_click(None)  # must not raise
    status = find_first(tree, lambda c: isinstance(c, ft.Text) and "boom" in (c.value or ""))
    assert status is not None
