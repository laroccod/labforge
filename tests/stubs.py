"""
Test stubs

A small but complete demo lab — a Gaussian sampler worker, a histogram viz and
a moments analysis, each branching on ScanResult — plus the fake pages and
control-tree walkers the smoke tests drive it with. Lives in tests/, not the
package: these are fixtures, not shipped API.
"""

import numpy as np

import flet as ft

from labforge import Lab, Param, ScanResult

THEORY = """
## The Gaussian law

The density of a normal variable with mean μ and standard deviation σ is

$$f(x) = \\frac{1}{\\sigma\\sqrt{2\\pi}} e^{-(x-\\mu)^2 / 2\\sigma^2}$$

and its first two moments determine it completely.
"""


def sample(mu=0.0, sigma=1.0, n=500, seed=42):
    """Draw n Gaussian variates; reproducible for a given seed."""
    return np.random.default_rng(seed).normal(mu, sigma, n)


def histogram(data, bins=40):
    """Density histogram of the draw; overlaid draws for a scan."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    if isinstance(data, ScanResult):
        for params, draws in data:
            label = ", ".join(f"{key}={params[key]:g}" for key in data.keys)
            ax.hist(draws, bins=bins, density=True, alpha=0.5, label=label)
        ax.legend()
    else:
        ax.hist(data, bins=bins, density=True)
    return fig, ax


def moments(data):
    """Sample mean and standard deviation, one row per grid point."""
    if isinstance(data, ScanResult):
        return [
            {**params, "mean": float(np.mean(draws)), "std": float(np.std(draws))}
            for params, draws in data
        ]
    return {"mean": float(np.mean(data)), "std": float(np.std(data))}


def make_lab():
    """Assemble the demo lab the smoke tests build pages against."""
    lab = Lab("testlab")
    lab.set_theory(THEORY)
    lab.add_worker(
        sample,
        {
            "mu": Param(default=0.0, bounds=(-5, 5), scan=True),
            "sigma": "scalar or array",
            "n": Param(kind="int", default=500, bounds=(10, 10_000)),
            "seed": "int",
        },
    )
    lab.add_viz(
        histogram,
        "Histogram",
        "Density histogram of the draw.",
        {"bins": Param(kind="int", default=40, bounds=(5, 200))},
    )
    lab.add_analysis(moments, "Moments", "Sample moments of the draw.")
    return lab


class FakePage:
    """Stand-in for ft.Page: builders only touch it inside (unfired) handlers."""

    def update(self):
        pass

    def run_task(self, handler, *args):
        # The real page schedules the coroutine on its loop; drive it to
        # completion here so a fired Run handler is synchronous for tests.
        import asyncio

        asyncio.run(handler(*args))


class ShellFakePage:
    """Richer stand-in supporting the attributes main() sets while wiring the shell."""

    def __init__(self):
        self.controls = []
        self.window = type("Window", (), {})()

    def add(self, *controls):
        self.controls.extend(controls)

    def update(self):
        pass


def find_first(control, predicate):
    """Depth-first search of a control subtree for the first match of predicate."""
    if control is None:
        return None
    if predicate(control):
        return control
    for child in getattr(control, "controls", None) or []:
        hit = find_first(child, predicate)
        if hit is not None:
            return hit
    return find_first(getattr(control, "content", None), predicate)


def collect_images(control, found=None):
    """Walk a control subtree and collect every ft.Image src encountered."""
    if found is None:
        found = []
    if control is None:
        return found
    if isinstance(control, ft.Image):
        found.append(control.src)
    # Recurse through the container shapes the pages actually use.
    for child in getattr(control, "controls", None) or []:
        collect_images(child, found)
    collect_images(getattr(control, "content", None), found)
    for row in getattr(control, "rows", None) or []:
        for cell in getattr(row, "cells", None) or []:
            collect_images(getattr(cell, "content", None), found)
    return found
