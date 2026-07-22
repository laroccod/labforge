"""
Param specs and the registration-time normalization of an author's spec dict.
"""

import inspect
import re
from dataclasses import dataclass


@dataclass
class Param:
    """
    One adjustable kwarg of a worker, viz or analysis function.

    Parameters
    ----------
    kind: str
        "scalar" (float), "int", or "tuple".
    default: object
        Starting value; filled from the function signature default when None.
    bounds: tuple
        (lo, hi) numeric range. Bounded scalars and ints render as sliders,
        unbounded ones as validated text fields.
    step: float
        Slider granularity; (hi - lo) / 100 when omitted, 1 for ints.
    scan: bool
        Worker kwargs only: accept comma-separated values to sweep a grid.
    size: int
        Tuple length (kind "tuple" only).
    label: str
        Control label; the kwarg name when omitted.
    """

    kind: str = "scalar"
    default: object = None
    bounds: tuple = None
    step: float = None
    scan: bool = False
    size: int = 2
    label: str = None


# Shorthand strings accepted in spec dicts, checked before the N-tuple pattern.
SHORTHANDS = {
    "scalar": dict(kind="scalar"),
    "int": dict(kind="int"),
    "array": dict(kind="scalar", scan=True),
    "scalar or array": dict(kind="scalar", scan=True),
    "int or array": dict(kind="int", scan=True),
}

TUPLE_PATTERN = re.compile(r"^(\d+)-tuple$")


def parse_shorthand(text):
    """
    Convert a shorthand string — a SHORTHANDS key or "N-tuple" (e.g. "2-tuple")
    — into a Param with kind/scan/size set; default left to signature inference.
    """
    key = text.strip().lower()
    if key in SHORTHANDS:
        return Param(**SHORTHANDS[key])
    match = TUPLE_PATTERN.match(key)
    if match:
        return Param(kind="tuple", size=int(match.group(1)))
    raise ValueError(
        f"Unknown param shorthand {text!r}; expected one of " f"{sorted(SHORTHANDS)} or 'N-tuple'."
    )


def infer_param(default):
    """Infer a Param from a signature default: bool/int, tuple, else scalar."""
    # bool before int: bool is an int subclass, and a checkbox-ish 0/1 is closer
    # to the author's intent than a float slider.
    if isinstance(default, bool):
        return Param(kind="int", default=int(default))
    if isinstance(default, int):
        return Param(kind="int", default=default)
    if isinstance(default, (tuple, list)):
        return Param(kind="tuple", default=tuple(default), size=len(default))
    return Param(kind="scalar", default=float(default))


def normalize_spec(func, spec, skip_first=False, allow_scan=True):
    """
    Validate a spec dict against a function signature and fill in defaults.

    Every named keyword-capable parameter of func gets a Param: spec entries
    (Param instances or shorthand strings) take precedence, and unspecced
    parameters are inferred from their signature defaults. Fails loudly at
    registration on unknown spec keys, unresolvable defaults, out-of-bounds
    defaults, or a scan spec where scanning is not allowed — so a malformed app
    dies at assembly rather than mid-navigation.

    Parameters
    ----------
    func: callable
        The registered worker, viz or analysis function.
    spec: dict
        {kwarg name: Param or shorthand str}, or None for pure inference.
    skip_first: bool
        Skip the leading positional parameter (the data argument of viz and
        analysis functions).
    allow_scan: bool
        Reject scan=True entries when False (scanning is a worker concept).

    Returns
    -------
    dict of {name: Param} in signature order, every default resolved.
    """
    spec = dict(spec or {})
    signature = inspect.signature(func)
    parameters = list(signature.parameters.values())
    if skip_first:
        parameters = parameters[1:]

    named = [
        p
        for p in parameters
        if p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    ]
    # A **kwargs function can take spec keys its signature never names.
    has_var_keyword = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in parameters)

    known = {p.name for p in named}
    for key in spec:
        if key not in known and not has_var_keyword:
            raise ValueError(f"{func.__name__} has no parameter {key!r}.")

    # Signature order drives the control layout; **kwargs-only entries trail it.
    normalized = {}
    order = [p.name for p in named] + [k for k in spec if k not in known]
    defaults = {p.name: p.default for p in named}
    for name in order:
        entry = spec.get(name)
        if isinstance(entry, str):
            entry = parse_shorthand(entry)
        # Resolve the default: spec first, signature second, error last.
        signature_default = defaults.get(name, inspect.Parameter.empty)
        if entry is None:
            if signature_default is inspect.Parameter.empty:
                raise ValueError(
                    f"{func.__name__} parameter {name!r} needs a spec entry or a "
                    "signature default."
                )
            entry = infer_param(signature_default)
        elif entry.default is None:
            if signature_default is inspect.Parameter.empty:
                raise ValueError(
                    f"{func.__name__} parameter {name!r} has no default in its spec "
                    "or signature."
                )
            entry.default = signature_default
        validate_param(func, name, entry, allow_scan)
        normalized[name] = entry
    return normalized


def validate_param(func, name, param, allow_scan):
    """
    Check one resolved Param's internal consistency, raising ValueError.

    Also coerces the default to the declared kind and fills a slider step for
    bounded params, so controls.py can trust both.
    """
    where = f"{func.__name__} parameter {name!r}"
    if param.kind not in ("scalar", "int", "tuple"):
        raise ValueError(f"{where}: unknown kind {param.kind!r}.")
    if param.scan and not allow_scan:
        raise ValueError(f"{where}: scan specs are only valid on the worker.")
    if param.kind == "tuple":
        if param.scan:
            raise ValueError(f"{where}: tuple params cannot be scanned.")
        param.default = tuple(param.default)
        if len(param.default) != param.size:
            raise ValueError(f"{where}: default {param.default} does not match size {param.size}.")
        return
    param.default = int(param.default) if param.kind == "int" else float(param.default)
    if param.bounds is not None:
        if len(param.bounds) != 2 or not param.bounds[0] < param.bounds[1]:
            raise ValueError(f"{where}: bounds must be an increasing (lo, hi) pair.")
        lo, hi = param.bounds
        if not lo <= param.default <= hi:
            raise ValueError(f"{where}: default {param.default} outside bounds {param.bounds}.")
        if param.step is None:
            param.step = 1 if param.kind == "int" else (hi - lo) / 100
