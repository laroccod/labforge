"""
Demo lab

The labforge README example in runnable form: a Gaussian sampler worker, a
histogram (with fitted density) and Q-Q plot visualization, and a moments
analysis, each handling both a single run and a parameter scan. Launch with
`python examples/demo_lab.py`; add `--browser [port]` to serve it to the
default web browser instead, `--scroll` for one continuous scrolling page
instead of four, and/or `--theme <name>` to try a colour scheme (see
labforge.themes()).
"""

import argparse
from pathlib import Path
from statistics import NormalDist

import matplotlib.pyplot as plt
import numpy as np

import labforge
from labforge import Lab, Param, ScanResult

lab = Lab("gausslab")
lab.set_theory(Path(__file__).with_name("theory.md"))


def sample(mu=0.0, sigma=1.0, n=2000, seed=42):
    """Draw n Gaussian variates; reproducible for a given seed."""
    return np.random.default_rng(seed).normal(mu, sigma, n)


lab.add_worker(
    sample,
    {
        "mu": Param(default=0.0, bounds=(-5, 5), scan=True),
        "sigma": Param(default=1.0, bounds=(0.1, 4), scan=True),
        "n": Param(kind="int", default=2000, bounds=(10, 100_000)),
        "seed": "int",
    },
)


def histogram(data, bins=40):
    """Density histogram of the draw; a scan overlays one histogram per point."""
    fig, ax = plt.subplots(figsize=(7, 3.4))
    if isinstance(data, ScanResult):
        for params, draws in data:
            label = ", ".join(f"{key} = {params[key]:g}" for key in data.keys)
            ax.hist(draws, bins=bins, density=True, alpha=0.5, label=label)
    else:
        colors = labforge.palette()
        ax.hist(data, bins=bins, density=True, color=colors.data, label="draw")
        # The density fitted by maximum likelihood, over the sample's own range.
        mean, std = np.mean(data), np.std(data, ddof=1)
        x = np.linspace(np.min(data), np.max(data), 400)
        pdf = np.exp(-((x - mean) ** 2) / (2 * std**2)) / (std * np.sqrt(2 * np.pi))
        ax.plot(x, pdf, color=colors.model, linewidth=1.6, label="fitted density")
    ax.legend()
    ax.set_xlabel("x")
    ax.set_ylabel("density")
    labforge.style(fig, ax)
    return fig, ax


lab.add_viz(
    histogram,
    "Histogram",
    "Density-normalized histogram of the most recent draw, with the "
    "maximum-likelihood normal density on top. On a scan, one translucent "
    "histogram per grid point shows how μ shifts and σ stretches the density.",
    {"bins": Param(kind="int", default=40, bounds=(5, 200))},
)


def qq_plot(data):
    """Standardized order statistics against normal quantiles; scans overlay grid points."""
    fig, ax = plt.subplots(figsize=(7, 3.4))
    colors = labforge.palette()

    def quantiles(draws):
        draws = np.asarray(draws)
        probs = (np.arange(1, len(draws) + 1) - 0.5) / len(draws)
        theory = np.array([NormalDist().inv_cdf(p) for p in probs])
        sample = np.sort((draws - np.mean(draws)) / np.std(draws, ddof=1))
        return theory, sample

    if isinstance(data, ScanResult):
        for params, draws in data:
            theory, sample = quantiles(draws)
            label = ", ".join(f"{key} = {params[key]:g}" for key in data.keys)
            ax.plot(theory, sample, linewidth=1.2, alpha=0.7, label=label)
    else:
        theory, sample = quantiles(data)
        ax.plot(theory, sample, linewidth=0, marker=".", markersize=3, color=colors.data)
    lims = ax.get_xlim()
    ax.plot(lims, lims, color=colors.model, linewidth=1.2, linestyle="--", label="diagonal")
    ax.legend()
    ax.set_xlabel("normal quantile")
    ax.set_ylabel("sample quantile")
    labforge.style(fig, ax)
    return fig, ax


lab.add_viz(
    qq_plot,
    "Q-Q plot",
    "Standardized order statistics of the draw against standard-normal "
    "quantiles. A Gaussian sample lies on the dashed diagonal, and "
    "standardizing collapses every grid point of a scan onto the same line.",
)


def moments(data):
    """Sample moments and the standard error of the mean; one row per grid point on a scan."""

    def row(draws):
        mean, std = float(np.mean(draws)), float(np.std(draws, ddof=1))
        return {"mean": mean, "std": std, "se(mean)": std / np.sqrt(len(draws))}

    if isinstance(data, ScanResult):
        return [{**params, **row(draws)} for params, draws in data]
    return row(data)


lab.add_analysis(
    moments,
    "Moments",
    "The sample mean and standard deviation estimate μ and σ directly, and "
    "for the normal family they are also the maximum-likelihood estimators. "
    "The standard error of the mean shrinks like 1/√n.",
)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the labforge Gaussian demo.")
    parser.add_argument(
        "--browser",
        nargs="?",
        const=0,
        type=int,
        metavar="PORT",
        help="serve to the default web browser (0 picks a free port)",
    )
    parser.add_argument("--scroll", action="store_true", help="one scrolling page, no rail")
    parser.add_argument("--theme", choices=labforge.themes(), help="colour scheme")
    args = parser.parse_args()

    # Only pass theme when --theme asks for one: open() already defaults to it,
    # so the demo never carries its own copy to drift.
    opts = {"layout": "scroll" if args.scroll else "pages"}
    if args.theme:
        opts["theme"] = args.theme
    if args.browser is not None:
        lab.open("browser", port=args.browser, **opts)
    else:
        lab.open(**opts)
