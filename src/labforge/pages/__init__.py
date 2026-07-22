"""
The stock page builders the shell navigates between.

Each exposes build(state, page) and is re-invoked on every visit
(rebuild-on-navigate), so a fresh build always reflects the latest LabState.
"""
