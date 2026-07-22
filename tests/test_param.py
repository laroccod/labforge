"""
Spec normalization tests

Pure-Python coverage of param.py: shorthand parsing, signature inference,
default resolution, and the registration-time ValueErrors.
"""

import pytest

from labforge.param import Param, normalize_spec, parse_shorthand


def worker(mu=0.0, sigma=1.0, n=2000):
    return mu + sigma + n


def viz(data, bins=40, xlims=(0.0, 1.0)):
    return data, bins, xlims


def test_shorthands():
    assert parse_shorthand("scalar") == Param(kind="scalar")
    assert parse_shorthand("int") == Param(kind="int")
    assert parse_shorthand("scalar or array") == Param(kind="scalar", scan=True)
    assert parse_shorthand("array") == Param(kind="scalar", scan=True)
    assert parse_shorthand("int or array") == Param(kind="int", scan=True)
    assert parse_shorthand("3-tuple") == Param(kind="tuple", size=3)
    with pytest.raises(ValueError):
        parse_shorthand("matrix")


def test_defaults_inferred_from_signature():
    spec = normalize_spec(worker, {"mu": "scalar or array", "n": "int"})
    assert spec["mu"].default == 0.0 and spec["mu"].scan
    assert spec["n"].default == 2000 and spec["n"].kind == "int"
    # sigma has no spec entry: inferred from its float signature default
    assert spec["sigma"] == Param(kind="scalar", default=1.0)
    assert list(spec) == ["mu", "sigma", "n"]  # signature order drives layout


def test_spec_default_wins_over_signature():
    spec = normalize_spec(worker, {"mu": Param(default=2.5, bounds=(-5, 5))})
    assert spec["mu"].default == 2.5
    assert spec["mu"].step == pytest.approx(0.1)  # (hi - lo) / 100


def test_skip_first_hides_the_data_argument():
    spec = normalize_spec(
        viz,
        {"bins": Param(kind="int", default=40, bounds=(5, 200))},
        skip_first=True,
        allow_scan=False,
    )
    assert list(spec) == ["bins", "xlims"]
    assert spec["xlims"] == Param(kind="tuple", default=(0.0, 1.0), size=2)


def test_registration_errors():
    with pytest.raises(ValueError, match="no parameter"):
        normalize_spec(worker, {"nope": "scalar"})
    with pytest.raises(ValueError, match="signature default"):
        normalize_spec(lambda x: x, None)
    with pytest.raises(ValueError, match="only valid on the worker"):
        normalize_spec(viz, {"bins": "int or array"}, skip_first=True, allow_scan=False)
    with pytest.raises(ValueError, match="outside bounds"):
        normalize_spec(worker, {"mu": Param(default=10.0, bounds=(-5, 5))})
    with pytest.raises(ValueError, match="increasing"):
        normalize_spec(worker, {"mu": Param(default=0.0, bounds=(5, -5))})
    with pytest.raises(ValueError, match="does not match size"):
        normalize_spec(viz, {"xlims": "3-tuple"}, skip_first=True, allow_scan=False)


def test_var_keyword_accepts_extra_spec_keys():
    def flexible(**kwargs):
        return kwargs

    spec = normalize_spec(flexible, {"gain": Param(default=1.0)})
    assert spec["gain"].default == 1.0
