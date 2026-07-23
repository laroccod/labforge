"""
Demo lab

Two samplers on one lab, to show off multiple workers and the Theory-page model
selector. A normal worker carries a histogram (with fitted density), a Q-Q plot
and a moments table; a gamma worker carries its own histogram and a
method-of-moments fit. The Theory-page dropdown is the single model switch
(selects_worker=True): choosing Normal or Gamma swaps the theory math and makes
that worker active, so the Simulation page shows its parameters as one tab and
the Visualization and Analysis pages show its own tabs. No top-bar worker
dropdown is needed. Each worker handles both a single run and a parameter scan.
Launch with `python examples/demo_lab.py`; add `--browser [port]` to serve it to
the default web browser instead, `--scroll` for one continuous scrolling page
instead of four, and/or `--theme <name>` to try a colour scheme (see
labforge.themes()).
"""

import argparse
from math import gamma as gamma_func
from pathlib import Path
from statistics import NormalDist

import matplotlib.pyplot as plt
import numpy as np

import labforge
from labforge import Lab, Param, ScanResult

lab = Lab("statlab")

# The Theory page carries a dropdown that swaps the whole page between the two
# families; each option maps to its own markdown source.
THEORY = {
    "Normal": Path(__file__).with_name("theory.md").read_text(encoding="utf-8"),
    "Gamma": Path(__file__).with_name("theory_gamma.md").read_text(encoding="utf-8"),
}


def theory_for(model):
    """The theory markdown for the selected distribution."""
    return THEORY[model]


lab.set_theory_selector(
    "model",
    Param(kind="choice", options=["Normal", "Gamma"], default="Normal"),
    theory_for,
    label="Distribution",
    selects_worker=True,
)


def sample(mu=0.0, sigma=1.0, n=2000, seed=42):
    """Draw n normal variates; reproducible for a given seed."""
    return np.random.default_rng(seed).normal(mu, sigma, n)


lab.add_worker(
    sample,
    {
        "mu": Param(default=0.0, bounds=(-5, 5), scan=True, help="Mean of the distribution"),
        "sigma": Param(
            default=1.0, bounds=(0.1, 4), scan=True, help="Standard deviation of the distribution"
        ),
        "n": Param(kind="int", default=2000, bounds=(10, 100_000), help="Sample size of the draw"),
        "seed": Param(kind="int", help="Seed of the random generator"),
    },
    name="Normal",
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


# The gamma worker. Registering a second worker turns the top bar into a model
# selector, and add_viz/add_analysis below attach to this worker, not the normal
# one, so each model owns its own tabs.
def sample_gamma(shape=2.0, scale=1.0, n=2000, seed=42):
    """Draw n gamma variates; reproducible for a given seed."""
    return np.random.default_rng(seed).gamma(shape, scale, n)


lab.add_worker(
    sample_gamma,
    {
        "shape": Param(default=2.0, bounds=(0.5, 10), scan=True, help="Shape parameter k"),
        "scale": Param(default=1.0, bounds=(0.1, 4), scan=True, help="Scale parameter θ"),
        "n": Param(kind="int", default=2000, bounds=(10, 100_000), help="Sample size of the draw"),
        "seed": Param(kind="int", help="Seed of the random generator"),
    },
    name="Gamma",
)


def gamma_density(x, shape, scale):
    """The gamma density at x for shape k and scale θ."""
    return x ** (shape - 1) * np.exp(-x / scale) / (scale**shape * gamma_func(shape))


def gamma_histogram(data, bins=40):
    """Density histogram of the draw; a scan overlays one histogram per point."""
    fig, ax = plt.subplots(figsize=(7, 3.4))
    if isinstance(data, ScanResult):
        for params, draws in data:
            label = ", ".join(f"{key} = {params[key]:g}" for key in data.keys)
            ax.hist(draws, bins=bins, density=True, alpha=0.5, label=label)
    else:
        colors = labforge.palette()
        ax.hist(data, bins=bins, density=True, color=colors.data, label="draw")
        # The method-of-moments fit: shape and scale from the sample mean and variance.
        mean, var = np.mean(data), np.var(data, ddof=1)
        shape, scale = mean**2 / var, var / mean
        x = np.linspace(np.min(data), np.max(data), 400)
        ax.plot(
            x,
            gamma_density(x, shape, scale),
            color=colors.model,
            linewidth=1.6,
            label="fitted density",
        )
    ax.legend()
    ax.set_xlabel("x")
    ax.set_ylabel("density")
    labforge.style(fig, ax)
    return fig, ax


lab.add_viz(
    gamma_histogram,
    "Histogram",
    "Density-normalized histogram of the most recent draw, with the "
    "method-of-moments gamma density on top. On a scan, one translucent "
    "histogram per grid point shows how the shape sharpens and the scale "
    "stretches the density.",
    {"bins": Param(kind="int", default=40, bounds=(5, 200))},
)


def gamma_fit(data):
    """Method-of-moments shape and scale from the sample moments; one row per grid point on a scan."""

    def row(draws):
        mean, var = float(np.mean(draws)), float(np.var(draws, ddof=1))
        return {"shape": mean**2 / var, "scale": var / mean, "mean": mean}

    if isinstance(data, ScanResult):
        return [{**params, **row(draws)} for params, draws in data]
    return row(data)


lab.add_analysis(
    gamma_fit,
    "Fit",
    "The mean is kθ and the variance is kθ², so the method of moments recovers "
    "the shape as X̄²/s² and the scale as s²/X̄. The maximum-likelihood shape "
    "has no closed form for this family, so the sample moments are the quick "
    "estimate.",
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
