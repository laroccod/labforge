"""
The scan engine: run the worker once, or over a cartesian grid of scan axes.

Pure Python, no Flet — unit-testable without a UI.
"""

import itertools
import math
from dataclasses import dataclass

from .param import CONTEXT_PARAM, wants_context


@dataclass
class ScanResult:
    """
    The collected output of a parameter scan.

    A list of (params, result) records rather than a tuple-keyed dict: records
    are self-describing (each carries its full kwarg dict), preserve cartesian
    order, and avoid float-equality lookups.

    Parameters
    ----------
    keys: list
        The scanned kwarg names, in control order.
    points: list
        (params dict, worker return) tuples, in cartesian-product order.
    """

    keys: list
    points: list

    def __iter__(self):
        return iter(self.points)

    def __len__(self):
        return len(self.points)

    def values(self):
        """The worker returns alone, in cartesian-product order."""
        return [value for _, value in self.points]

    def axis(self, key):
        """The distinct values one scanned kwarg took, in entry order."""
        return list(dict.fromkeys(params[key] for params, _ in self.points))


def run_worker(func, values, context=None, progress=None):
    """
    Call the worker once, or over the cartesian grid of its scan axes.

    The worker always receives scalars: an axis is expanded into one call per
    grid point, never passed through as a list. Viz and analysis functions tell
    the two cases apart with isinstance(data, ScanResult).

    Parameters
    ----------
    func: callable
        The registered worker.
    values: dict
        Parsed control values; list-valued entries are scan axes.
    context: dict
        The lab's shared context, injected as a `context` kwarg only when func
        declares that parameter; the scan grid never sweeps it.
    progress: callable
        Optional progress(done, total), called after each grid point of a scan
        so a UI can report a long sweep; never called for a scalar run.

    Returns
    -------
    The worker's bare return for a pure-scalar call, or a ScanResult when any
    axis is a list.
    """
    shared = {CONTEXT_PARAM: context} if wants_context(func) else {}
    axes = {key: value for key, value in values.items() if isinstance(value, list)}
    if not axes:
        return func(**values, **shared)

    fixed = {key: value for key, value in values.items() if key not in axes}
    total = math.prod(len(axis) for axis in axes.values())
    points = []
    for combo in itertools.product(*axes.values()):
        params = dict(fixed, **dict(zip(axes.keys(), combo)))
        points.append((params, func(**params, **shared)))
        if progress is not None:
            progress(len(points), total)
    return ScanResult(keys=list(axes.keys()), points=points)
