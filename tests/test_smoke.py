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

from stubs import FakePage, ShellFakePage, collect_images, find_first, histogram, make_lab


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
    # Viz and Analysis tabs are explorable before the first run; the run gate
    # sits in each entry's output slot rather than replacing the page.
    viz_tree = visualization.build(state, page)
    assert find_first(viz_tree, lambda c: isinstance(c, ft.TabBar)) is not None
    gate = find_first(viz_tree, lambda c: isinstance(c, ft.Text) and c.value == "NO DATA")
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
    assert not button.disabled  # re-enabled once the run settles


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
    # the Simulation section precedes the results, so the first FilledButton in
    # depth-first order is Run even with the Render/Compute buttons now built
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


def test_several_workers_need_a_selection_mechanism():
    import pytest

    from labforge import Lab

    # No top-bar dropdown exists, so several workers with neither a model
    # selector nor tabs view have no way to be chosen — caught at build.
    lab = Lab("multi")
    lab.add_worker(lambda mu=0.0: [mu])
    lab.add_worker(lambda kk=1.0: [kk], name="beta")
    with pytest.raises(ValueError, match="choose among them"):
        lab.build_main()


def test_single_worker_shell_has_no_selector():
    state_page = ShellFakePage()
    make_lab().build_main()(state_page)
    dropdown = find_first(state_page.controls[0], lambda c: isinstance(c, ft.Dropdown))
    assert dropdown is None


def make_choice_lab():
    from labforge import Lab, Param

    lab = Lab("choicelab")

    def pick(mode="fast", gain=1.0):
        return [gain if mode == "fast" else -gain]

    lab.add_worker(pick, {"mode": Param(kind="choice", options=["fast", "slow"])})
    return lab


def test_choice_param_renders_a_dropdown():
    state = LabState(make_choice_lab())
    tree = simulation.build(state, FakePage())
    dropdown = find_first(tree, lambda c: isinstance(c, ft.Dropdown))
    assert dropdown is not None
    assert [o.key for o in dropdown.options] == ["fast", "slow"]
    assert dropdown.value == "fast"


def make_selector_lab():
    from labforge import Lab, Param

    lab = Lab("selectorlab")
    lab.set_theory_selector(
        "model",
        Param(kind="choice", options=["Alpha", "Beta"]),
        lambda selection: f"# {selection}\n\n$$E = {selection}^2$$",
    )
    lab.add_worker(lambda x=1.0: [x])
    return lab


def test_theory_selector_page_renders_and_rebuilds():
    from types import SimpleNamespace

    state = LabState(make_selector_lab())
    tree = theory.build(state, FakePage())

    # The selector dropdown and the model-driven equation both render.
    dropdown = find_first(tree, lambda c: isinstance(c, ft.Dropdown))
    assert dropdown is not None
    assert [o.key for o in dropdown.options] == ["Alpha", "Beta"]
    assert [src for src in collect_images(tree) if src]  # the $$...$$ block rendered

    # Selecting a model commits to the shared context and rebuilds the markdown.
    dropdown.value = "Beta"
    dropdown.on_select(SimpleNamespace(control=SimpleNamespace(value="Beta")))
    assert state.context["model"] == "Beta"
    heading = find_first(tree, lambda c: isinstance(c, ft.Markdown) and "Beta" in (c.value or ""))
    assert heading is not None


def make_tabbed_lab():
    from labforge import Lab, Param

    lab = Lab("tabbedlab", worker_view="tabs")
    lab.set_theory_selector(
        "model", Param(kind="choice", options=["m1", "m2"]), lambda selection: f"# {selection}"
    )

    def step_a(mu=0.0, context=None):
        return [mu]

    def step_b(k=1.0, context=None):
        return [k]

    lab.add_worker(step_a)
    lab.add_worker(step_b, name="step_b")
    lab.add_viz(histogram, "Histogram", "Shared across workers.")
    return lab


def test_tabbed_simulation_renders_workers_as_tabs():
    state = LabState(make_tabbed_lab())
    tree = simulation.build(state, FakePage())

    # Both workers are tabs, and there is no run gate on the Simulation page.
    tabbar = find_first(tree, lambda c: isinstance(c, ft.TabBar))
    assert tabbar is not None
    assert [t.label for t in tabbar.tabs] == ["step_a", "step_b"]
    gate = find_first(tree, lambda c: isinstance(c, ft.Text) and c.value == "NO DATA")
    assert gate is None

    # Running the second worker's tab lights the shared visualization.
    buttons = []
    find_first(tree, lambda c: buttons.append(c) if isinstance(c, ft.FilledButton) else False)
    buttons[-1].on_click(None)
    assert state.has_data()
    images = [src for src in collect_images(visualization.build(state, FakePage())) if src]
    assert images


def test_tabbed_shell_has_no_worker_dropdown():
    from labforge import Lab

    # No Theory selector here, so the only Dropdown that could appear is a
    # top-bar worker selector — which tabs view must not surface.
    lab = Lab("barelab", worker_view="tabs")
    lab.add_worker(lambda mu=0.0: [mu])
    lab.add_worker(lambda k=1.0: [k], name="second")
    state_page = ShellFakePage()
    lab.build_main()(state_page)
    dropdown = find_first(state_page.controls[0], lambda c: isinstance(c, ft.Dropdown))
    assert dropdown is None  # workers are Simulation-page tabs, not a top-bar selector
    # The top bar shows a plain tab-count readout in its place.
    readout = find_first(
        state_page.controls[0], lambda c: isinstance(c, ft.Text) and "TABS" in (c.value or "")
    )
    assert readout is not None


def test_model_selector_drives_the_worker_and_single_sim_tab():
    from types import SimpleNamespace

    from labforge import Lab, Param

    lab = Lab("modellab")
    lab.set_theory_selector(
        "model",
        Param(kind="choice", options=["Normal", "Gamma"], default="Normal"),
        lambda selection: f"# {selection}",
        selects_worker=True,
    )
    lab.add_worker(lambda mu=0.0: [mu], {"mu": Param(default=0.0, bounds=(-5, 5))}, name="Normal")
    lab.add_worker(
        lambda shape=2.0: [shape], {"shape": Param(default=2.0, bounds=(0.5, 10))}, name="Gamma"
    )

    state_page = ShellFakePage()
    lab.build_main()(state_page)
    tree = state_page.controls[0]

    # No top-bar worker dropdown; a MODELS count readout stands in its place.
    readout = find_first(tree, lambda c: isinstance(c, ft.Text) and "MODELS" in (c.value or ""))
    assert readout is not None

    rail = find_first(tree, lambda c: isinstance(c, ft.NavigationRail))
    rail.on_change(SimpleNamespace(control=SimpleNamespace(selected_index=1)))
    # Simulation shows the active worker as one tab, with its own control.
    tabbar = find_first(tree, lambda c: isinstance(c, ft.TabBar))
    assert [t.label for t in tabbar.tabs] == ["Normal"]
    assert find_first(tree, lambda c: isinstance(c, ft.Text) and c.value == "mu") is not None

    # The Theory model dropdown switches the active worker.
    rail.on_change(SimpleNamespace(control=SimpleNamespace(selected_index=0)))
    model_dd = find_first(tree, lambda c: isinstance(c, ft.Dropdown))
    model_dd.value = "Gamma"
    model_dd.on_select(SimpleNamespace(control=SimpleNamespace(value="Gamma")))

    rail.on_change(SimpleNamespace(control=SimpleNamespace(selected_index=1)))
    tabbar = find_first(tree, lambda c: isinstance(c, ft.TabBar))
    assert [t.label for t in tabbar.tabs] == ["Gamma"]
    assert find_first(tree, lambda c: isinstance(c, ft.Text) and c.value == "shape") is not None
    assert find_first(tree, lambda c: isinstance(c, ft.Text) and c.value == "mu") is None


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
    assert not button.disabled  # the finally re-enables Run even on failure
