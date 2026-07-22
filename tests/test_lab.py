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


def test_second_worker_raises():
    lab = make_lab()
    with pytest.raises(ValueError, match="one worker"):
        lab.add_worker(worker)


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
