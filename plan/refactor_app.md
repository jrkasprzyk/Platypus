## Refactor Plan: Split `gui/app.py` into focused modules

### Current State
All GUI code lives in a single 777-line `gui/app.py`. It mixes five concerns: small helpers (`_subscript`, `_hiplot_available`), the `Tooltip` widget, problem/algorithm registries and factories, the `Worker` thread, and the large `App(tk.Tk)` class which itself spans UI construction, event handling, queue polling, plotting, and HiPlot export. The only external surface is `gui.app:main` and the `python -m gui.app` entry point — `gui/__init__.py` is empty and nothing imports internals from this package.

### Target State
`gui/` becomes a small package of focused modules. `app.py` keeps only the `App` controller class plus `main()`; drawing logic, registries, worker, tooltip, and HiPlot export each move to their own file. Pure drawing functions take an `Axes` and data so they can be unit-tested without a Tk root. Public entry point (`gui.app:main`, `python -m gui.app`) is unchanged.

### Affected Files
| File | Change Type | Dependencies |
|------|-------------|--------------|
| `gui/app.py` | modify (shrink to App + main) | blocked by all new modules |
| `gui/tooltip.py` | create | none |
| `gui/registries.py` | create | none (imports plotypus) |
| `gui/worker.py` | create | blocked by `registries` |
| `gui/plotting.py` | create | none (matplotlib only) |
| `gui/hiplot_export.py` | create | none |
| `gui/__init__.py` | optional: re-export `main` | blocked by `app.py` |
| `dev/completed_plans/feature-gui-parallel-axes-1.md` | no change | — |

### Execution Plan

#### Phase 1: Extract leaf modules (no `App` changes)
- [ ] Step 1.1: Create `gui/tooltip.py` containing the `Tooltip` class verbatim (lines 48–70).
- [ ] Step 1.2: Create `gui/registries.py` containing `PROBLEMS`, `ALGORITHMS`, `make_problem`, `_nsgaiii_divisions`, `make_algorithm` (lines 18–26 imports + 77–174). Keep `make_algorithm` and `_nsgaiii_divisions` together since the latter is private to it.
- [ ] Step 1.3: Create `gui/plotting.py` containing:
  - `_SUBSCRIPT_DIGITS` and `subscript()` (renamed from `_subscript`, made public)
  - `draw_parallel_axes(ax, rows, axis_labels, *, …)` (from `_draw_parallel_axes`, lines 690–736) — already pure
  - `draw_placeholder(ax)` — one-axes version of the loop in `_draw_placeholders`
  - `draw_pareto_cartesian(ax, result)` — extracted from lines 574–610, returns nothing; caller handles axes reset and canvas.draw
  - `draw_pareto_parallel(ax, result, current_nobjs)` — extracted from 612–639
  - `draw_progress_cartesian(ax, nfe_hist, size_hist)` — extracted from 649–660
  - `draw_progress_parallel(ax, last_result, nfe_hist)` — extracted from 662–686
- [ ] Step 1.4: Create `gui/hiplot_export.py` containing `hiplot_available()` (from `_hiplot_available`, lines 37–43) and `open_in_hiplot(last_result)` — takes the result list, raises on failure; caller shows the messagebox. Keeps lazy imports inside the function.
- [ ] Step 1.5: Create `gui/worker.py` containing the `Worker` class (lines 179–214), importing `make_algorithm` from `gui.registries`.
- [ ] Verify after each step: `python -c "import gui.tooltip, gui.registries, gui.plotting, gui.hiplot_export, gui.worker"` succeeds. `python -c "import gui.app"` still works (old file untouched).

#### Phase 2: Rewire `gui/app.py`
- [ ] Step 2.1: Replace the in-file definitions in `app.py` with imports from the new modules:
  - `from gui.tooltip import Tooltip`
  - `from gui.registries import PROBLEMS, ALGORITHMS, make_problem`
  - `from gui.worker import Worker`
  - `from gui import plotting`
  - `from gui.hiplot_export import hiplot_available, open_in_hiplot`
- [ ] Step 2.2: Drop now-unused imports from `app.py` (`math`, `statistics`, `tempfile`, `threading`, the plotypus problem/algo names). Keep `queue`, `tkinter`, `webbrowser`, `messagebox`, `matplotlib`, `Figure`, `FigureCanvasTkAgg`, `NavigationToolbar2Tk`.
- [ ] Step 2.3: Replace the bodies of `_draw_placeholders`, `_redraw_pareto_cartesian`, `_redraw_pareto_parallel`, `_redraw_progress_cartesian`, `_redraw_progress_parallel`, and `_draw_parallel_axes` with thin wrappers that call into `plotting.*`, handle the axes-3D-reset decision, and call `self._canvas_*.draw()`. The 3D-vs-2D axes swap (`_reset_pareto_axes`) stays on `App` because it touches Tk-managed figure state.
- [ ] Step 2.4: Replace `_open_in_hiplot` body with a `try/except` that calls `open_in_hiplot(self._last_result)` and shows the messagebox on error / empty result.
- [ ] Step 2.5: Replace `_hiplot_available()` call site with `hiplot_available()`.
- [ ] Verify: `python -m gui.app` launches, default Cartesian run on DTLZ2 (2 obj and 3 obj) shows expected plots, view toggle to "Parallel axes" works on both tabs, Stop button works, HiPlot button state matches `hiplot_available()`.

#### Phase 3: Optional tidy
- [ ] Step 3.1: In `gui/__init__.py`, add `from gui.app import main` so `from gui import main` works. Skip if the team prefers `__init__.py` stay empty.
- [ ] Step 3.2: Remove dead comments / section banners in `app.py` that no longer match the (now-shorter) content.

#### Phase 4: Validation
- [ ] `python -c "import gui.app"` — smoke import.
- [ ] `python -m gui.app` — launch GUI, run DTLZ2 (2 obj), DTLZ2 (3 obj), ZDT3, CF8 to spot-check Pareto/Progress in both view modes, Stop mid-run, and HiPlot export (if `parasolpy`/`hiplot` installed).
- [ ] `git diff --stat` — confirm `app.py` shrank substantially and new files exist.

### Rollback Plan
If something breaks during Phase 2:
1. `git restore gui/app.py` to revert to the single-file version (new modules are unused and harmless).
2. If a new module has a bug, delete it and inline that section back into `app.py` until fixed.

If a regression is caught after Phase 2 lands:
1. `git revert` the refactor commit — no schema or data migrations involved.

### Risks
- **Hidden coupling on private names.** `_subscript` and `_draw_parallel_axes` are referenced via `self.`/module-private names; renaming during extraction could break a call site I missed. Mitigation: grep for each name after each extraction step.
- **Axes-state ownership.** The plotting helpers must not assume axes projection (2D vs 3D); `_reset_pareto_axes` must stay on `App`. Mitigation: keep that method untouched and call it from `App` before invoking `plotting.draw_pareto_cartesian` when `nobjs` crosses the 2D/3D boundary, just as today.
- **Lazy imports for HiPlot.** `parasolpy`/`hiplot`/`pandas` must remain imported inside the function, not at module top, so `import gui.hiplot_export` works without those installed (TEST-007 in the parallel-axes plan).
- **Circular imports.** `worker.py` imports from `registries.py`; `app.py` imports from both. No cycles, but keep `plotting.py` free of `gui.app` references.
- **No automated tests exist.** Validation is manual GUI smoke-testing — be deliberate about exercising both view modes and the 2D↔3D objective transition.
