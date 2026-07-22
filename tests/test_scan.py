"""
Scan engine tests

Pure-Python coverage of scan.py: the scalar pass-through, cartesian expansion,
and the ScanResult helpers.
"""

from labforge.scan import ScanResult, run_worker


def worker(mu, sigma, n):
    return (mu, sigma, n)


def test_scalar_run_returns_bare_value():
    data = run_worker(worker, {"mu": 0.0, "sigma": 1.0, "n": 100})
    assert data == (0.0, 1.0, 100)
    assert not isinstance(data, ScanResult)


def test_scan_expands_cartesian_grid():
    values = {"mu": [0.0, 1.0, 2.0], "sigma": [0.5, 1.0, 1.5, 2.0], "n": 100}
    data = run_worker(worker, values)
    assert isinstance(data, ScanResult)
    assert len(data) == 12
    assert data.keys == ["mu", "sigma"]
    # cartesian order: mu varies slowest, sigma fastest
    first_params, first_value = data.points[0]
    assert first_params == {"mu": 0.0, "sigma": 0.5, "n": 100}
    assert first_value == (0.0, 0.5, 100)
    last_params, _ = data.points[-1]
    assert last_params == {"mu": 2.0, "sigma": 2.0, "n": 100}


def test_scan_result_helpers():
    data = run_worker(worker, {"mu": [0.0, 1.0], "sigma": 1.0, "n": 10})
    assert data.axis("mu") == [0.0, 1.0]
    assert data.values() == [(0.0, 1.0, 10), (1.0, 1.0, 10)]
    assert [params["mu"] for params, _ in data] == [0.0, 1.0]


def test_context_injected_only_when_declared():
    def with_context(mu, context=None):
        return (mu, context)

    ctx = {"model": "alpha"}
    # A declared context param is handed the dict at every grid point; the scan
    # never sweeps it.
    scalar = run_worker(with_context, {"mu": 1.0}, context=ctx)
    assert scalar == (1.0, ctx)
    scanned = run_worker(with_context, {"mu": [1.0, 2.0]}, context=ctx)
    assert scanned.values() == [(1.0, ctx), (2.0, ctx)]
    # A worker without a context param is unaffected by a passed context.
    assert run_worker(worker, {"mu": 0.0, "sigma": 1.0, "n": 5}, context=ctx) == (0.0, 1.0, 5)
