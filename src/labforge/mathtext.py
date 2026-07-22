"""
Render LaTeX math to a base64 PNG: system LaTeX when present, matplotlib's
mathtext otherwise.

Flet has no equation widget, and an image renders identically on every platform.
"""

import base64
import io
import os
import shutil

import matplotlib

matplotlib.use("Agg")  # headless: render to a buffer, never open a window
import matplotlib.pyplot as plt

from . import theme

# Rendered at 2x, displayed at 1x, so equations stay crisp on retina screens.
RENDER_DPI = 220
DISPLAY_SCALE = 0.5

# amssymb supplies \mathbb; amsmath the spacing/alignment macros the prose uses;
# eulervm sets the math font to Euler (Zapf), the app's mathematical voice.
LATEX_PREAMBLE = r"\usepackage{amsmath}\usepackage{amssymb}\usepackage[euler-digits]{eulervm}"

# MacTeX installs its binaries here, but a GUI-launched process may not inherit it
# on PATH — add it so both the availability probe and matplotlib's subprocess find
# latex/dvipng.
TEX_BIN = "/Library/TeX/texbin"
if os.path.isdir(TEX_BIN) and TEX_BIN not in os.environ.get("PATH", "").split(os.pathsep):
    os.environ["PATH"] = TEX_BIN + os.pathsep + os.environ.get("PATH", "")


def latex_available():
    """True when a system LaTeX toolchain (latex + dvipng) is on PATH."""
    return bool(shutil.which("latex") and shutil.which("dvipng"))


# Probed once at import. A render failure later (missing package, unsupported
# glyph) latches this off for the session, since that failure mode is systemic and
# retrying it pays a slow subprocess timeout on every equation.
USE_LATEX = latex_available()


def render_png(latex, fontsize, usetex):
    """
    Render a LaTeX math string to a base64 PNG and its display size.

    Parameters
    ----------
    latex: str
        Math content without surrounding dollar signs, e.g. r"f(x)=\\lambda".
    fontsize: int
        Point size of the rendered equation.
    usetex: bool
        Compile with the system LaTeX toolchain when True, else use mathtext.
        The usetex path accepts the full LaTeX command set (\\mathbb, \\mathcal,
        alignment environments) that mathtext only partly supports, and sets the
        math font to Euler; mathtext's cost is a narrower vocabulary and
        Computer-Modern glyphs.

    Returns
    -------
    Tuple of (base64 src, width in inches, height in inches).
    """
    # rc_context keeps usetex local to this figure, so it never touches an
    # author's own plots.
    rc = {"text.usetex": usetex}
    if usetex:
        rc["text.latex.preamble"] = LATEX_PREAMBLE
    else:
        # Computer Modern, not matplotlib's sans-serif default, so the fallback
        # keeps a serif math voice near the usetex path's Euler.
        rc["mathtext.fontset"] = "cm"
    with plt.rc_context(rc):
        fig = plt.figure()
        # Displayed equations get display style — full-size fractions, sum
        # limits above and below. Only usetex knows \displaystyle; the mathtext
        # fallback keeps text style, one more of its accepted costs.
        body = f"\\displaystyle {latex}" if usetex else latex
        # Ink follows the active theme, so equations sit on the app surface the
        # transparent PNG is composited onto rather than fighting it.
        text = fig.text(0, 0, f"${body}$", fontsize=fontsize, color=theme.active().ink)

        # Measure the drawn text so we can crop the canvas tightly around it.
        fig.canvas.draw()
        bbox = text.get_window_extent()
        pad = fontsize * 0.35
        width_in = (bbox.width + 2 * pad) / fig.dpi
        height_in = (bbox.height + 2 * pad) / fig.dpi
        fig.set_size_inches(width_in, height_in)
        text.set_position((pad / bbox.width if bbox.width else 0.1, 0.5))
        text.set_verticalalignment("center")

        buffer = io.BytesIO()
        fig.savefig(
            buffer,
            format="png",
            dpi=RENDER_DPI,
            transparent=True,
            bbox_inches="tight",
            pad_inches=0.08,
        )
        plt.close(fig)

    src = base64.b64encode(buffer.getvalue()).decode("ascii")
    return src, width_in, height_in


def equation_image(latex, fontsize=18):
    """
    Render a LaTeX math string to a base64 PNG suitable for ft.Image.

    Prefers the system LaTeX toolchain and falls back to mathtext when it is
    absent or a render fails, so a page never blanks on an equation.

    Parameters
    ----------
    latex: str
        Math content without surrounding dollar signs, e.g. r"f(x)=\\lambda".
    fontsize: int
        Point size of the rendered equation.

    Returns
    -------
    dict with base64 src plus display width and height in logical pixels.
    """
    global USE_LATEX
    if USE_LATEX:
        try:
            src, width_in, height_in = render_png(latex, fontsize, usetex=True)
        except Exception:
            USE_LATEX = False
            src, width_in, height_in = render_png(latex, fontsize, usetex=False)
    else:
        src, width_in, height_in = render_png(latex, fontsize, usetex=False)

    return {
        "src": src,
        "width": width_in * RENDER_DPI * DISPLAY_SCALE,
        "height": height_in * RENDER_DPI * DISPLAY_SCALE,
    }
