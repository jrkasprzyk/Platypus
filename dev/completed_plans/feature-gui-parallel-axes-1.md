---
goal: Add a Cartesian/Parallel-axes plot toggle to the Plotypus Explorer GUI for both the Pareto Front and Progress tabs, with optional parasolpy/HiPlot export.
version: 1.0
date_created: 2026-05-17
last_updated: 2026-05-17
owner: Joseph Kasprzyk
status: 'Planned'
tags: [feature, gui, visualization]
---

# Introduction

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

The Plotypus Explorer (`gui/app.py`) currently renders results in Cartesian coordinates: a 2D/3D scatter for the Pareto Front tab and a 2D line plot for the Progress tab. This plan adds a per-tab "Plot view" toggle that swaps the Cartesian view with a Matplotlib-native parallel-axes (parallel-coordinates) view. Parallel coordinates scale to arbitrary objective counts (>3) where 3D scatter degrades, and they make tradeoff inspection across many objectives possible. A secondary "Open in HiPlot…" action invokes `parasolpy.parallel_plot_hp` to render a richer interactive HTML view in the user's browser.

## 1. Requirements & Constraints

- **REQ-001**: User can toggle each plot tab (Pareto Front, Progress) between "Cartesian" and "Parallel axes" via a dropdown/radio in the sidebar or per-tab toolbar.
- **REQ-002**: Toggle works during a live run — switching views must redraw using the most recent snapshot (`self._nfe_hist`, `self._size_hist`, last `result`).
- **REQ-003**: Pareto-Front parallel view shows one polyline per non-dominated solution across `nobjs` normalized axes labeled `f₁ … f_n`.
- **REQ-004**: Progress parallel view shows per-objective summary statistics (min / median / max of the most recent population) across `nobjs` axes, OR a parallel-coords plot of the latest population colored by `f₁` — exact choice resolved by **DEC-001** (see §3).
- **REQ-005**: Parallel-axes rendering must use Matplotlib only (no Plotly/Dash/HiPlot) so it embeds in the existing `FigureCanvasTkAgg`.
- **REQ-006**: An "Open in HiPlot…" button writes an HTML file via `parasolpy.parallel_plot_hp(...).to_html(path)` and opens it in the default browser via `webbrowser.open`.
- **REQ-007**: Switching the toggle must not interrupt the worker thread or lose accumulated history.
- **CON-001**: Must not introduce a hard dependency on parasolpy. `parasolpy` and `hiplot` imports must be lazy and guarded; if missing, the "Open in HiPlot…" button is disabled with a tooltip explaining how to install.
- **CON-002**: No new threads; all drawing happens on the Tk main thread inside `_poll`/`_apply_update`.
- **CON-003**: Preserve existing public behavior — running, stopping, status, progressbar, About dialog must be unchanged.
- **GUD-001**: Follow the existing code style in `gui/app.py` — `ttk` widgets, `Tooltip` helper, `_redraw_*` naming, leading-underscore private members.
- **GUD-002**: Keep the parallel-coordinates renderer self-contained in `gui/app.py`; no new modules unless reused.
- **PAT-001**: Follow the existing pattern of `_reset_pareto_axes` / `_redraw_pareto` / `_redraw_progress` — add `_redraw_pareto_parallel` and `_redraw_progress_parallel`, plus a dispatcher that picks based on the toggle state.

## 2. Implementation Steps

### Implementation Phase 1 — State, toggles, and dispatch

- GOAL-001: Add per-tab view-mode state and UI controls without changing render output yet.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-001 | In `App.__init__` (`gui/app.py` ~line 209), add `self._pareto_view = tk.StringVar(value="cartesian")` and `self._progress_view = tk.StringVar(value="cartesian")`. | | |
| TASK-002 | In `_build_plots` (~line 339), above each canvas add a small `ttk.Frame` containing `ttk.Label(text="View:")` and a `ttk.Combobox` bound to the corresponding StringVar with values `["Cartesian", "Parallel axes"]`, `state="readonly"`, width 14. Bind `<<ComboboxSelected>>` to `self._on_pareto_view_change` and `self._on_progress_view_change`. | | |
| TASK-003 | Add `Tooltip(combo, "Switch between Cartesian (scatter/line) and parallel-axes (one polyline per solution across normalized objective axes) views.")` for both comboboxes. | | |
| TASK-004 | Add a new private member `self._last_result: list[list[float]] = []` set inside `_apply_update` before calling redraw helpers, so view toggles after a run can re-render without re-running. | | |
| TASK-005 | Implement `_on_pareto_view_change(self, _event=None)` and `_on_progress_view_change(self, _event=None)` that call `self._redraw_pareto(self._last_result)` and `self._redraw_progress()` respectively. | | |
| TASK-006 | Refactor `_redraw_pareto` into a dispatcher: if `self._pareto_view.get() == "Parallel axes"` call `self._redraw_pareto_parallel(result)`, else call existing `_redraw_pareto_cartesian(result)` (rename current body). | | |
| TASK-007 | Refactor `_redraw_progress` similarly into a dispatcher with `_redraw_progress_cartesian` (current body) and `_redraw_progress_parallel`. | | |
| TASK-008 | In `_reset_pareto_axes`, when switching view mode, always recreate axes as 2D for parallel mode (no 3D projection) even if `nobjs >= 3`. | | |

### Implementation Phase 2 — Matplotlib parallel-axes renderer

- GOAL-002: Implement a self-contained normalized parallel-coordinates renderer used by both tabs.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-009 | Add private helper `_draw_parallel_axes(ax, rows, axis_labels, *, color_by=None, cmap="viridis", alpha=0.5, lw=0.8, title=None)` where `rows` is a 2D iterable of shape `(n_solutions, n_axes)`. | | |
| TASK-010 | Inside `_draw_parallel_axes`: compute per-axis min/max from `rows`; for each axis index `j` plot a vertical line via `ax.axvline(j, color="#cccccc", lw=0.8, zorder=0)`; set `ax.set_xticks(range(n_axes))` and `ax.set_xticklabels(axis_labels)`; set `ax.set_xlim(-0.2, n_axes-1+0.2)`; set `ax.set_yticks([])`; draw left-side numeric tick labels for the first axis using `ax.text` at `(-0.1, 0.0)` and `(-0.1, 1.0)` showing original min/max. | | |
| TASK-011 | Inside `_draw_parallel_axes`: normalize each column to `[0, 1]` via `(v - min) / (max - min)` with a `1e-12` guard against zero range. For each solution row, `ax.plot(range(n_axes), normalized_row, color=..., alpha=alpha, lw=lw)`. | | |
| TASK-012 | Implement `color_by` mode: if provided, map each row's `color_by` value through `matplotlib.cm.get_cmap(cmap)` over the value's normalized range and pass per-line `color=`. Default `color_by=None` uses a single color `#2577c8`. | | |
| TASK-013 | Implement `_redraw_pareto_parallel(self, result)`: guard empty result; compute `nobjs = len(result[0])`; build `axis_labels = [f"f{_subscript(i+1)}" for i in range(nobjs)]` (reuse the same subscript characters already used: `f₁`, `f₂`, …); call `_draw_parallel_axes(self._ax_pareto, result, axis_labels, color_by=[r[0] for r in result], cmap="viridis", title=f"Pareto Front (parallel)  ·  {len(result)} solutions")`; `self._canvas_pareto.draw()`. | | |
| TASK-014 | Implement `_redraw_progress_parallel(self)`: if `self._last_result` is empty, clear axes and return; compute per-objective `min`, `median`, `max` across the latest population using `statistics.median` and built-ins; pass three rows to `_draw_parallel_axes` with `axis_labels = [f"f{_subscript(i+1)}" for i in range(nobjs)]`, custom line colors `["#2577c8", "#1e7d1e", "#b87a00"]`, and a legend via `ax.legend(["min", "median", "max"], loc="upper right")`; title `f"Progress (parallel)  ·  NFE {self._nfe_hist[-1]:,}"`. | | |
| TASK-015 | Add helper `def _subscript(n: int) -> str` near the top of the module that returns the Unicode-subscript form of an integer (e.g., `12 -> "₁₂"`). Use it consistently in both Cartesian and parallel labelers. | | |

### Implementation Phase 3 — Optional HiPlot export via parasolpy

- GOAL-003: Provide a one-click "Open in HiPlot…" path that uses `parasolpy.parallel_plot_hp` and opens the rendered HTML in the user's browser, without making parasolpy a hard dependency.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-016 | At module top, add lazy availability probe: `def _hiplot_available() -> bool: try: import parasolpy, hiplot; return True; except Exception: return False`. Do NOT import at module top — import inside the handler. | | |
| TASK-017 | In `_build_plots`, beside the Pareto-tab view combobox add `ttk.Button(text="Open in HiPlot…", command=self._open_in_hiplot)`. Disable the button if `not _hiplot_available()` and attach a `Tooltip` reading "Install `parasolpy` and `hiplot` (pip install parasolpy hiplot) to enable interactive HiPlot export." | | |
| TASK-018 | Implement `_open_in_hiplot(self)`: if `not self._last_result`, `messagebox.showinfo("HiPlot export", "Run an algorithm first.")` and return; build a `pandas.DataFrame` with columns `[f"f{i+1}" for i in range(nobjs)]` from `self._last_result`; import `parasolpy` lazily; call `exp = parasolpy.parallel_plot_hp(df, obj_names=list(df.columns), obj_directions=["minimize"]*nobjs)`; write to `tempfile.NamedTemporaryFile(suffix=".html", delete=False)` via `exp.to_html(path)`; `webbrowser.open(f"file:///{path}")`. | | |
| TASK-019 | Wrap the export in `try/except Exception as e` and surface failures via `messagebox.showerror("HiPlot export failed", str(e))`. | | |

### Implementation Phase 4 — Wiring, polish, and verification

- GOAL-004: Integrate, verify with each problem class, and finalize.

| Task | Description | Completed | Date |
|------|-------------|-----------|------|
| TASK-020 | In `_draw_placeholders`, ensure placeholder text remains correct in both view modes (parallel view should still show the centered "Run an algorithm to see results" text on an empty 2D axis). | | |
| TASK-021 | In `_reset_pareto_axes`, when `self._pareto_view.get() == "Parallel axes"`, always create a plain `add_subplot(111)` regardless of `nobjs`. | | |
| TASK-022 | In `_apply_update`, set `self._last_result = result` before the existing `_redraw_pareto(result)` call so subsequent view toggles work without re-running. | | |
| TASK-023 | Run `python -m gui.app` (or the existing entry point) and manually verify: (a) default Cartesian behavior unchanged; (b) toggle to Parallel during a 3-obj DTLZ2 run shows polylines; (c) 8-obj DTLZ2 run renders cleanly on the Pareto tab parallel view; (d) HiPlot button opens browser when parasolpy is installed; (e) HiPlot button is disabled with tooltip when parasolpy is uninstalled in a fresh venv. | | |
| TASK-024 | Update `gui/__init__.py` only if a new public export is needed (likely none). | | |

## 3. Alternatives

- **ALT-001**: Embed `plotly` parallel coordinates directly in Tk via `plotly` → HTML → CEF/embedded browser widget. Rejected: heavy dependency (CEF / PyWebView), large install footprint, breaks the all-Matplotlib rendering pipeline.
- **ALT-002**: Use `pandas.plotting.parallel_coordinates`. Rejected: requires a class/label column and produces less-polished output; rolling our own gives full control over axis ticks, normalization, and per-line coloring.
- **ALT-003**: Use `parasolpy.parallel_plot_hp` as the *primary* renderer (always HTML in a browser). Rejected: breaks the live-update loop and the in-app embedded-canvas UX, and would force `parasolpy` + `hiplot` to become hard dependencies. Kept as a secondary "Open in HiPlot…" action instead.
- **ALT-004**: Make Progress's parallel view a population-level parallel-coords plot (one polyline per current solution, colored by `f₁`) instead of min/median/max summary. **DEC-001**: prototype both, default to min/median/max (TASK-014) for live-update legibility; revisit after PR review.

## 4. Dependencies

- **DEP-001**: `matplotlib` (already required).
- **DEP-002**: `tkinter` / `ttk` (stdlib).
- **DEP-003**: `parasolpy>=0.2.1` — **optional**, only used by TASK-018. Probed via `_hiplot_available()`.
- **DEP-004**: `hiplot` — **optional**, transitive of `parasolpy`. Probed via `_hiplot_available()`.
- **DEP-005**: `pandas` — only needed inside `_open_in_hiplot`; already a transitive dependency of parasolpy, so it is present whenever HiPlot export is available.

## 5. Files

- **FILE-001**: `gui/app.py` — primary changes: view-mode state (Phase 1), parallel-axes renderer (Phase 2), HiPlot export button + handler (Phase 3).
- **FILE-002**: `plan/feature-gui-parallel-axes-1.md` — this plan.

## 6. Testing

- **TEST-001**: Manual — DTLZ2 with `nobjs=2`, toggle Pareto view between Cartesian and Parallel mid-run; both render and live-update without exceptions.
- **TEST-002**: Manual — DTLZ2 with `nobjs=8`, toggle to Parallel; expect 8 vertical axes labeled `f₁ … f₈` with one polyline per non-dominated solution.
- **TEST-003**: Manual — ZDT1 (nobjs fixed at 2), Cartesian view unchanged, parallel view shows two axes.
- **TEST-004**: Manual — Stop a run mid-way, switch view; verify re-render uses last snapshot (`self._last_result`).
- **TEST-005**: Manual — In a venv without `parasolpy`, confirm "Open in HiPlot…" is disabled and tooltip explains install path.
- **TEST-006**: Manual — In a venv with `parasolpy` installed, click "Open in HiPlot…" after a 5-obj DTLZ2 run; verify default browser opens a HiPlot HTML file with five axes.
- **TEST-007**: Smoke — `python -c "import gui.app"` succeeds whether or not `parasolpy` is installed (lazy-import guarantee).

## 7. Risks & Assumptions

- **RISK-001**: Per-line `ax.plot` calls scale O(n_solutions × n_objs); for very large populations (pop_size > 1000) live updates may stutter. Mitigation: if `len(result) > 500`, downsample via `result[::max(1, len(result)//500)]` inside `_redraw_pareto_parallel`.
- **RISK-002**: Switching `_ax_pareto` between 3D and 2D projections requires `_reset_pareto_axes`; if the user toggles rapidly during a live update, a transient `AttributeError` on `set_zlabel` could occur. Mitigation: TASK-021 always re-creates a plain 2D axis when entering Parallel view.
- **RISK-003**: `parasolpy.parallel_plot_hp` signature assumes `obj_directions` of equal length to `obj_names`; the export handler currently passes all `"minimize"`. Plotypus benchmarks are minimization-only, so this is consistent — but if a future user passes maximization problems through this GUI, results will look inverted. Flag in docstring of `_open_in_hiplot`.
- **ASSUMPTION-001**: All Plotypus benchmark problems exposed in the GUI are minimization problems (consistent with current `PROBLEMS` registry).
- **ASSUMPTION-002**: `parasolpy` will remain available as an editable install at `C:\github\parasolpy` on the developer's machine for manual TEST-006; users without it should fall back to the disabled-button path (TEST-005).

## 8. Related Specifications / Further Reading

- parasolpy `parallel_plot_hp` — `C:\github\parasolpy\parasolpy\tradeoff.py` (lines 92–277).
- parasolpy Dash variant — `C:\github\parasolpy\parasolpy\dash_tools.py`.
- HiPlot documentation — https://facebookresearch.github.io/hiplot/
- Matplotlib parallel coordinates reference — https://matplotlib.org/stable/gallery/specialty_plots/parallel_coordinates.html
- Existing GUI source — `gui/app.py`.
