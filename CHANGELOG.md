# Changelog

Notable changes to labforge. Versions follow [semantic versioning](https://semver.org).

## 0.2.0 — 2026-07-22

- **`choice` param** — `Param(kind="choice", options=[...])` renders a Dropdown
  and commits the selected string like any other control. The default must be
  one of the options and the options must be non-empty (checked at registration);
  a choice cannot be scanned.
- **Theory-page selector** — `set_theory_selector(name, param, theory)` puts a
  `choice` control on the Theory page whose value both rebuilds the theory
  markdown (via a `theory(selection) -> markdown` callback) and writes the lab's
  shared context. The static `set_theory` behavior is unchanged; the selector
  takes precedence when both are set.
- **Model-driven worker selector** — `set_theory_selector(..., selects_worker=True)`
  makes the Theory dropdown the model switch: its options name registered workers,
  and choosing one makes that worker active. The Simulation page then shows the
  active worker as a single tab so it matches the tabbed Visualization and
  Analysis pages.
- **Shared context** — a per-session lab-level context that the Theory selector
  writes and any worker, viz or analysis reads by declaring a `context`
  parameter (injected at call time, never rendered as a control). So a choice is
  made once and every page sees it.
- **Multiple workers** — call `add_worker` more than once to build a lab with
  several workers. Each worker keeps its own workspace (controls, last result,
  and per-tab settings), and the `add_viz` / `add_analysis` calls after each
  `add_worker` attach that worker's own tabs. Several workers need a way to choose
  among them, checked at build: a `selects_worker` model selector, or
  `worker_view="tabs"` to lay the workers out as Simulation-page tabs (sharing one
  set of visualizations and analyses). There is no top-bar worker dropdown.
  Single-worker labs are unchanged. (`worker_view` is `"panels"` by default, or
  `"tabs"`.)
- **Bundled fonts** — the app now ships its typefaces (Inter and Roboto Mono),
  so the browser view renders the same faces and weights as the desktop window
  instead of falling back to the platform default.
- **Clearer theory errors** — `set_theory` now raises on a mistyped file path
  (a missing `Path`, or a bare `".md"` string) instead of silently rendering the
  path as a one-line page.
- **Non-blocking Run** — the worker now runs off the UI thread, so a slow worker
  no longer freezes the window. Run shows a `RUNNING…` status and disables the
  button until the run settles. Fast workers are unaffected.

## 0.1.1 — 2026-07-22

Packaging and documentation only; no functional change.

- Complete PyPI metadata: `readme`, keywords, trove classifiers, and project
  URLs, so the project page renders the README and links back to the repository.
- README image links use absolute URLs, so screenshots and the theme gallery
  render on the PyPI project page rather than showing as broken images.

## 0.1.0 — 2026-07-22

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
