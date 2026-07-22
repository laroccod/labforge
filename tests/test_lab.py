"""
Registration tests

Coverage of lab.py's registration-time validation and state.py's run flow,
without building any Flet controls.
"""

import pytest

from labforge import Lab, Param, ScanResult
from labforge.state import LabState


def worker(mu=0.0, sigma=1.0, n=100):
    return [mu] * n


def histogram(data, bins=40):
    return data, bins


def make_lab():
    lab = Lab("testlab")
    lab.add_worker(worker, {"mu": Param(default=0.0, bounds=(-5, 5), scan=True)})
    lab.add_viz(histogram, "Histogram", "A histogram.")
    return lab


def test_duplicate_worker_name_raises():
    lab = make_lab()
    with pytest.raises(ValueError, match="already registered"):
        lab.add_worker(worker)  # same func.__name__


def test_multiple_workers_own_their_tabs():
    lab = Lab("multi")

    def draw_a(mu=0.0):
        return [mu]

    def draw_b(k=1):
        return [k]

    lab.add_worker(draw_a)
    lab.add_viz(histogram, "Hist A")
    lab.add_worker(draw_b, name="beta")
    lab.add_analysis(lambda data: {"n": len(data)}, "Count B")

    assert list(lab.workers) == ["draw_a", "beta"]
    # add_viz/add_analysis attach to the worker most recently added.
    assert [v.title for v in lab.workers["draw_a"].vizzes] == ["Hist A"]
    assert lab.workers["draw_a"].analyses == []
    assert lab.workers["beta"].vizzes == []
    assert [a.title for a in lab.workers["beta"].analyses] == ["Count B"]


def test_build_main_requires_a_worker():
    with pytest.raises(ValueError, match="add_worker"):
        Lab("empty").build_main()


def test_scan_spec_rejected_on_viz():
    lab = Lab("testlab")
    with pytest.raises(ValueError, match="only valid on the worker"):
        lab.add_viz(histogram, "Histogram", spec={"bins": "int or array"})


def test_open_rejects_unknown_view():
    with pytest.raises(ValueError, match="view must be"):
        make_lab().open("tablet")


def test_set_theory_accepts_raw_markdown_and_paths(tmp_path):
    lab = Lab("testlab")
    lab.set_theory("# Raw markdown")
    assert lab.theory_source == "# Raw markdown"
    path = tmp_path / "theory.md"
    path.write_text("# From a file")
    lab.set_theory(path)
    assert lab.theory_source == "# From a file"


def test_set_theory_rejects_mistyped_path(tmp_path):
    lab = Lab("testlab")
    # A missing Path, or a bare .md string, is a typo — fail loudly, not silently.
    with pytest.raises(ValueError, match="no such file"):
        lab.set_theory(tmp_path / "missing.md")
    with pytest.raises(ValueError, match="no such file"):
        lab.set_theory("theroy.md")
    # Prose that merely mentions a .md file is still rendered as markdown.
    lab.set_theory("See notes.md for details.")
    assert lab.theory_source == "See notes.md for details."


def test_state_seeds_defaults_and_runs():
    state = LabState(make_lab())
    assert state.worker_values == {"mu": 0.0, "sigma": 1.0, "n": 100}
    assert state.viz_values == {"Histogram": {"bins": 40}}
    assert not state.has_data()

    state.run()
    assert state.has_data()
    assert state.n_points == 1
    assert len(state.data) == 100
    assert "RUN COMPLETE · 1 POINT" in state.run_summary

    state.worker_values["mu"] = [0.0, 1.0, 2.0]
    state.run()
    assert isinstance(state.data, ScanResult)
    assert state.n_points == 3
    assert "3 POINTS · 1 AXIS" in state.run_summary


def test_state_stashes_each_workers_workspace():
    lab = Lab("multi")
    lab.add_worker(worker, {"mu": Param(default=0.0, bounds=(-5, 5))})
    lab.add_worker(lambda k=2: [k] * k, name="beta")

    state = LabState(lab)
    assert state.active == "worker"
    state.worker_values["mu"] = 3.0
    state.run()
    assert state.has_data()

    # Switching workers exposes a fresh, ungated workspace...
    state.set_worker("beta")
    assert not state.has_data()
    assert state.worker_values == {"k": 2}
    state.run()
    assert state.n_points == 1

    # ...and switching back restores the first worker's run and edits intact.
    state.set_worker("worker")
    assert state.has_data()
    assert state.worker_values["mu"] == 3.0


def test_set_theory_selector_requires_a_choice_param():
    lab = Lab("testlab")
    with pytest.raises(ValueError, match="choice Param"):
        lab.set_theory_selector("model", Param(default=0.0), lambda selection: selection)


def test_theory_selector_seeds_shared_context():
    lab = make_lab()
    lab.set_theory_selector(
        "model",
        Param(kind="choice", options=["alpha", "beta"]),
        lambda selection: f"# {selection}",
    )
    assert lab.theory_selector.param.default == "alpha"  # first option
    # The shared context is seeded, per session, with the selector's default.
    state = LabState(lab)
    assert state.context == {"model": "alpha"}


def test_worker_receives_shared_context():
    seen = {}

    def sampler(mu=0.0, context=None):
        seen["context"] = context
        return [mu]

    lab = Lab("ctxlab")
    lab.set_theory_selector(
        "model", Param(kind="choice", options=["m1", "m2"]), lambda selection: selection
    )
    lab.add_worker(sampler)
    state = LabState(lab)
    state.context["model"] = "m2"
    state.run()
    assert seen["context"] == {"model": "m2"}


def test_tabbed_workers_register_shared_tabs():
    lab = Lab("tabbed", worker_view="tabs")
    lab.add_worker(worker, {"mu": Param(default=0.0, bounds=(-5, 5))})
    lab.add_worker(lambda k=2: [k] * k, name="beta")
    lab.add_viz(histogram, "Histogram")  # lab-level, shared across workers

    assert list(lab.workers) == ["worker", "beta"]
    # In tabs view viz attach to the lab, not to any one worker.
    assert [v.title for v in lab.shared_vizzes] == ["Histogram"]
    assert lab.workers["worker"].vizzes == []

    # Data and the run gate span every worker; running one lights the shared viz.
    state = LabState(lab)
    assert state.vizzes is lab.shared_vizzes
    assert not state.has_data()
    state.run("beta")
    assert state.has_data()
    assert state.last_run == "beta"
    assert list(state.data) == [2, 2]


def test_bad_worker_view_rejected():
    with pytest.raises(ValueError, match="worker_view must be"):
        Lab("bad", worker_view="grid")


def make_model_lab():
    """A two-worker lab whose Theory selector is the active-worker switch."""
    lab = Lab("modellab")
    lab.set_theory_selector(
        "model",
        Param(kind="choice", options=["Normal", "Gamma"], default="Gamma"),
        lambda selection: f"# {selection}",
        selects_worker=True,
    )
    lab.add_worker(lambda mu=0.0: [mu], name="Normal")
    lab.add_worker(lambda shape=2.0: [shape], name="Gamma")
    return lab


def test_selects_worker_seeds_active_from_selector_default():
    lab = make_model_lab()
    assert lab.selects_worker
    # The selector default (Gamma), not the first worker (Normal), opens active.
    state = LabState(lab)
    assert state.active == "Gamma"
    assert state.context == {"model": "Gamma"}


def test_selects_worker_options_must_name_workers():
    lab = Lab("badmodel")
    lab.set_theory_selector(
        "model",
        Param(kind="choice", options=["Normal", "Poisson"]),
        lambda selection: selection,
        selects_worker=True,
    )
    lab.add_worker(lambda mu=0.0: [mu], name="Normal")
    # Poisson names no worker; caught at build, once both are registered.
    with pytest.raises(ValueError, match="must name workers"):
        lab.build_main()
