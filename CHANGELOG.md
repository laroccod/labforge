# Changelog

Notable changes to labforge. Versions follow [semantic versioning](https://semver.org).

## 0.1.0 — unreleased

Initial release.

- **`Lab`** — register plain Python functions (one worker, any number of
  visualization and analysis functions) and a markdown theory source, then
  `open()` the assembled app: as a native desktop window or served to the
  browser, laid out as four rail-navigated pages or one continuous scrolling
  page. All registration is validated on the spot, so a malformed app fails at
  assembly rather than mid-navigation.
- **`Param` specs** — each worker/viz/analysis kwarg gets a UI control from its
  `Param` (or a shorthand string such as `"int"` or `"scalar or array"`);
  bounded params render as sliders with live readouts, unbounded ones as
  validated text fields, tuples as per-element fields. Defaults are inferred
  from the function signature.
- **Parameter scans** — a kwarg declared `scan=True` accepts comma-separated
  values; the worker runs once per point of the cartesian grid and downstream
  functions receive a `ScanResult` of `(params, result)` records.
- **Analysis dispatch** — an analysis may return a dict (two-column table), a
  list of dicts or a DataFrame (table), a string (markdown), or a matplotlib
  figure; the return shape picks the rendering.
- **Themes** — eight palettes selected by `open(theme=...)`, four dark and
  four light; chrome, plot palette and equation ink move together, and
  `labforge.palette()` / `labforge.style(fig, ax)` let an author's figures
  follow the active theme.
- **LaTeX theory** — `$$...$$` blocks in the theory markdown render as crisp
  equation images via system LaTeX, falling back to matplotlib mathtext.
- **MIT licensed.**
