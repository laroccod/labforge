"""
The scan engine: run the worker once, or over a cartesian grid of scan axes.

Pure Python, no Flet — unit-testable without a UI.
"""

import itertools
from dataclasses import dataclass


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


def run_worker(func, values):
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

    Returns
    -------
    The worker's bare return for a pure-scalar call, or a ScanResult when any
    axis is a list.
    """
    axes = {key: value for key, value in values.items() if isinstance(value, list)}
    if not axes:
        return func(**values)

    fixed = {key: value for key, value in values.items() if key not in axes}
    points = []
    for combo in itertools.product(*axes.values()):
        params = dict(fixed, **dict(zip(axes.keys(), combo)))
        points.append((params, func(**params)))
    return ScanResult(keys=list(axes.keys()), points=points)
