#!/usr/bin/env python3
"""Plotypus Explorer — GUI for multiobjective optimization."""

import math
import queue
import statistics
import tempfile
import threading
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from plotypus import (
    EpsMOEA, EpsNSGAII, GDE3, IBEA, MOEAD, NSGAII, NSGAIII, OMOPSO, SMPSO, SPEA2,
    DTLZ1, DTLZ2, DTLZ3, DTLZ4, DTLZ7,
    ZDT1, ZDT2, ZDT3, ZDT4, ZDT5, ZDT6,
    WFG1, WFG2, WFG3, WFG4, WFG5, WFG6, WFG7, WFG8, WFG9,
    UF1, UF2, UF3, UF4, UF5, UF6, UF7, UF8, UF9, UF10, UF11, UF12, UF13,
    CF1, CF2, CF3, CF4, CF5, CF6, CF7, CF8, CF9, CF10,
    Schaffer, Belegundu,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

_SUBSCRIPT_DIGITS = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def _subscript(n: int) -> str:
    return str(n).translate(_SUBSCRIPT_DIGITS)


def _hiplot_available() -> bool:
    try:
        import parasolpy  # noqa: F401
        import hiplot  # noqa: F401
        return True
    except Exception:
        return False


# ── Tooltip helper ────────────────────────────────────────────────────────────

class Tooltip:
    """Lightweight hover tooltip for any tkinter widget."""

    def __init__(self, widget, text):
        self._widget = widget
        self._text = text
        self._tip = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _event=None):
        x = self._widget.winfo_rootx() + self._widget.winfo_width() + 4
        y = self._widget.winfo_rooty()
        self._tip = tw = tk.Toplevel(self._widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self._text, justify="left", background="#ffffe0",
                 relief="solid", borderwidth=1, font=("Segoe UI", 8),
                 wraplength=220).pack()

    def _hide(self, _event=None):
        if self._tip:
            self._tip.destroy()
            self._tip = None


# ── Registries ────────────────────────────────────────────────────────────────

# (class, accepts nobjs kwarg)
PROBLEMS = {
    "DTLZ1": (DTLZ1, True),
    "DTLZ2": (DTLZ2, True),
    "DTLZ3": (DTLZ3, True),
    "DTLZ4": (DTLZ4, True),
    "DTLZ7": (DTLZ7, True),
    "ZDT1":  (ZDT1,  False),
    "ZDT2":  (ZDT2,  False),
    "ZDT3":  (ZDT3,  False),
    "ZDT4":  (ZDT4,  False),
    "ZDT5":  (ZDT5,  False),
    "ZDT6":  (ZDT6,  False),
    "WFG1":  (WFG1,  True),
    "WFG2":  (WFG2,  True),
    "WFG3":  (WFG3,  True),
    "WFG4":  (WFG4,  True),
    "WFG5":  (WFG5,  True),
    "WFG6":  (WFG6,  True),
    "WFG7":  (WFG7,  True),
    "WFG8":  (WFG8,  True),
    "WFG9":  (WFG9,  True),
    "UF1":   (UF1,   False),
    "UF2":   (UF2,   False),
    "UF3":   (UF3,   False),
    "UF4":   (UF4,   False),
    "UF5":   (UF5,   False),
    "UF6":   (UF6,   False),
    "UF7":   (UF7,   False),
    "UF8":   (UF8,   False),
    "UF9":   (UF9,   False),
    "UF10":  (UF10,  False),
    "UF11":  (UF11,  False),
    "UF12":  (UF12,  False),
    "UF13":  (UF13,  False),
    "CF1":   (CF1,   False),
    "CF2":   (CF2,   False),
    "CF3":   (CF3,   False),
    "CF4":   (CF4,   False),
    "CF5":   (CF5,   False),
    "CF6":   (CF6,   False),
    "CF7":   (CF7,   False),
    "CF8":   (CF8,   False),
    "CF9":   (CF9,   False),
    "CF10":  (CF10,  False),
    "Schaffer":   (Schaffer,   False),
    "Belegundu":  (Belegundu,  False),
}

# display name -> key used in make_algorithm()
ALGORITHMS = {
    "NSGA-II":   "nsgaii",
    "NSGA-III":  "nsgaiii",
    "MOEA/D":    "moead",
    "IBEA":      "ibea",
    "SPEA2":     "spea2",
    "GDE3":      "gde3",
    "OMOPSO":    "omopso",
    "SMPSO":     "smpso",
    "ε-MOEA":    "epsmoea",
    "ε-NSGA-II": "epsnsgaii",
}


def make_problem(name, nobjs):
    cls, accepts_nobjs = PROBLEMS[name]
    return cls(nobjs=nobjs) if accepts_nobjs else cls()


def _nsgaiii_divisions(nobjs, target_pop):
    div = 1
    while math.comb(nobjs + div - 1, div) < target_pop:
        div += 1
    return div


def make_algorithm(key, problem, pop_size):
    if key == "nsgaii":
        return NSGAII(problem, population_size=pop_size)
    if key == "nsgaiii":
        div = _nsgaiii_divisions(problem.nobjs, pop_size)
        return NSGAIII(problem, divisions_outer=div)
    if key == "moead":
        return MOEAD(problem, population_size=pop_size)
    if key == "ibea":
        return IBEA(problem, population_size=pop_size)
    if key == "spea2":
        return SPEA2(problem, population_size=pop_size)
    if key == "gde3":
        return GDE3(problem, population_size=pop_size)
    if key == "omopso":
        return OMOPSO(problem, epsilons=[0.05], swarm_size=pop_size)
    if key == "smpso":
        return SMPSO(problem, swarm_size=pop_size)
    if key == "epsmoea":
        return EpsMOEA(problem, epsilons=[0.05], population_size=pop_size)
    if key == "epsnsgaii":
        return EpsNSGAII(problem, epsilons=[0.05], population_size=pop_size)
    raise ValueError(f"Unknown algorithm: {key}")


# ── Worker thread ─────────────────────────────────────────────────────────────

class Worker(threading.Thread):
    def __init__(self, msg_q, problem, algo_key, pop_size, max_nfe, update_freq):
        super().__init__(daemon=True)
        self.q = msg_q
        self.problem = problem
        self.algo_key = algo_key
        self.pop_size = pop_size
        self.max_nfe = max_nfe
        self.update_freq = update_freq
        self._stop_event = threading.Event()

    def request_stop(self):
        self._stop_event.set()

    def run(self):
        try:
            algo = make_algorithm(self.algo_key, self.problem, self.pop_size)
            state = {"last": 0}

            def cb(a):
                if self._stop_event.is_set():
                    raise InterruptedError
                if a.nfe - state["last"] >= self.update_freq:
                    state["last"] = a.nfe
                    snap = [list(s.objectives[:]) for s in a.result]
                    self.q.put({"t": "update", "nfe": a.nfe, "result": snap})

            algo.run(self.max_nfe, callback=cb)
            final = [list(s.objectives[:]) for s in algo.result]
            self.q.put({"t": "done", "nfe": algo.nfe, "result": final})

        except InterruptedError:
            self.q.put({"t": "stopped"})
        except Exception as e:
            import traceback
            self.q.put({"t": "error", "msg": str(e), "tb": traceback.format_exc()})


# ── Main application ──────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Plotypus Explorer")
        self.geometry("1150x700")
        self.minsize(800, 500)

        style = ttk.Style()
        style.theme_use("vista")

        self._worker: Worker | None = None
        self._queue: queue.Queue = queue.Queue()
        self._nfe_hist: list[int] = []
        self._size_hist: list[int] = []
        self._max_nfe = 10000
        self._current_nobjs = 2
        self._last_result: list[list[float]] = []
        self._pareto_view = tk.StringVar(value="Cartesian")
        self._progress_view = tk.StringVar(value="Cartesian")

        self._build_ui()
        self._build_menu()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_menu(self):
        menubar = tk.Menu(self)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Documentation",
                              command=lambda: webbrowser.open(
                                  "https://plotypus.readthedocs.io"))
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menubar)

    def _show_about(self):
        import plotypus
        messagebox.showinfo(
            "About Plotypus Explorer",
            f"Plotypus Explorer\n"
            f"Version {plotypus.__version__}\n\n"
            f"A GUI for multiobjective optimization\n"
            f"built on the Plotypus framework.\n\n"
            f"https://plotypus.readthedocs.io"
        )

    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_plots()

    def _build_sidebar(self):
        side = ttk.Frame(self, padding=(12, 12, 8, 12))
        side.grid(row=0, column=0, sticky="ns")

        r = 0
        ttk.Label(side, text="Plotypus Explorer", font=("Segoe UI", 12, "bold")).grid(
            row=r, column=0, columnspan=2, pady=(0, 14)); r += 1

        # ── Problem ──
        ttk.Label(side, text="Problem", font=("Segoe UI", 9, "bold")).grid(
            row=r, column=0, columnspan=2, sticky="w", pady=(0, 2)); r += 1

        ttk.Label(side, text="Problem").grid(row=r, column=0, sticky="w")
        self._problem_var = tk.StringVar(value="DTLZ2")
        prob_cb = ttk.Combobox(side, textvariable=self._problem_var,
                               values=list(PROBLEMS), state="readonly", width=10)
        prob_cb.grid(row=r, column=1, pady=2, padx=(6, 0), sticky="e"); r += 1
        prob_cb.bind("<<ComboboxSelected>>", self._on_problem_change)
        Tooltip(prob_cb, "Benchmark problem to optimize. DTLZ/WFG support variable objective counts; ZDT/UF/CF are fixed at 2.")

        ttk.Label(side, text="Objectives").grid(row=r, column=0, sticky="w")
        self._nobjs_var = tk.IntVar(value=2)
        self._nobjs_spin = ttk.Spinbox(side, from_=2, to=8,
                                       textvariable=self._nobjs_var, width=5)
        self._nobjs_spin.grid(row=r, column=1, pady=2, padx=(6, 0), sticky="e"); r += 1
        Tooltip(self._nobjs_spin, "Number of objectives for the selected problem (disabled for problems with a fixed objective count).")

        ttk.Separator(side, orient="horizontal").grid(
            row=r, column=0, columnspan=2, sticky="ew", pady=8); r += 1

        # ── Algorithm ──
        ttk.Label(side, text="Algorithm", font=("Segoe UI", 9, "bold")).grid(
            row=r, column=0, columnspan=2, sticky="w", pady=(0, 2)); r += 1

        ttk.Label(side, text="Algorithm").grid(row=r, column=0, sticky="w")
        self._algo_var = tk.StringVar(value="NSGA-II")
        algo_cb = ttk.Combobox(side, textvariable=self._algo_var,
                               values=list(ALGORITHMS), state="readonly", width=10)
        algo_cb.grid(row=r, column=1, pady=2, padx=(6, 0), sticky="e"); r += 1
        Tooltip(algo_cb, "Multiobjective evolutionary algorithm to run.")

        ttk.Label(side, text="Pop size").grid(row=r, column=0, sticky="w")
        self._pop_var = tk.IntVar(value=100)
        pop_spin = ttk.Spinbox(side, from_=10, to=2000, increment=10,
                               textvariable=self._pop_var, width=7)
        pop_spin.grid(row=r, column=1, pady=2, padx=(6, 0), sticky="e"); r += 1
        Tooltip(pop_spin, "Number of candidate solutions maintained each generation. Larger values improve coverage but increase runtime.")

        ttk.Label(side, text="Max NFE").grid(row=r, column=0, sticky="w")
        self._nfe_var = tk.IntVar(value=10000)
        nfe_entry = ttk.Entry(side, textvariable=self._nfe_var, width=8)
        nfe_entry.grid(row=r, column=1, pady=2, padx=(6, 0), sticky="e"); r += 1
        Tooltip(nfe_entry, "Maximum number of function evaluations (NFE). The algorithm stops after this many calls to the problem's objective functions.")

        ttk.Label(side, text="Update every").grid(row=r, column=0, sticky="w")
        self._freq_var = tk.IntVar(value=500)
        freq_spin = ttk.Spinbox(side, from_=50, to=5000, increment=50,
                                textvariable=self._freq_var, width=7)
        freq_spin.grid(row=r, column=1, pady=2, padx=(6, 0), sticky="e"); r += 1
        Tooltip(freq_spin, "Refresh the plot every N function evaluations. Lower values give smoother live updates; higher values are faster.")

        ttk.Separator(side, orient="horizontal").grid(
            row=r, column=0, columnspan=2, sticky="ew", pady=8); r += 1

        # ── Controls ──
        self._run_btn = ttk.Button(side, text="▶  Run", command=self._run, width=16)
        self._run_btn.grid(row=r, column=0, columnspan=2, pady=2); r += 1

        self._stop_btn = ttk.Button(side, text="■  Stop", command=self._stop,
                                    state="disabled", width=16)
        self._stop_btn.grid(row=r, column=0, columnspan=2, pady=2); r += 1

        ttk.Separator(side, orient="horizontal").grid(
            row=r, column=0, columnspan=2, sticky="ew", pady=8); r += 1

        # ── Progress ──
        ttk.Label(side, text="Progress", font=("Segoe UI", 9, "bold")).grid(
            row=r, column=0, columnspan=2, sticky="w", pady=(0, 4)); r += 1

        self._progress = ttk.Progressbar(side, length=180, mode="determinate")
        self._progress.grid(row=r, column=0, columnspan=2, pady=2); r += 1

        self._nfe_label = ttk.Label(side, text="NFE: —", font=("Consolas", 9))
        self._nfe_label.grid(row=r, column=0, columnspan=2, pady=(2, 0)); r += 1

        self._status_label = ttk.Label(side, text="Ready", foreground="#666666")
        self._status_label.grid(row=r, column=0, columnspan=2, pady=(2, 0)); r += 1

    def _build_plots(self):
        right = ttk.Frame(self, padding=(0, 8, 8, 8))
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        nb = ttk.Notebook(right)
        nb.grid(sticky="nsew")

        # Tab 1 — Pareto front
        t1 = ttk.Frame(nb)
        nb.add(t1, text="  Pareto Front  ")
        t1.rowconfigure(1, weight=1)
        t1.columnconfigure(0, weight=1)

        bar1 = ttk.Frame(t1)
        bar1.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 0))
        ttk.Label(bar1, text="View:").pack(side="left")
        pareto_combo = ttk.Combobox(bar1, textvariable=self._pareto_view,
                                    values=["Cartesian", "Parallel axes"],
                                    state="readonly", width=14)
        pareto_combo.pack(side="left", padx=(4, 0))
        pareto_combo.bind("<<ComboboxSelected>>", self._on_pareto_view_change)
        Tooltip(pareto_combo, "Switch between Cartesian (scatter/line) and parallel-axes (one polyline per solution across normalized objective axes) views.")

        self._hiplot_btn = ttk.Button(bar1, text="Open in HiPlot…",
                                      command=self._open_in_hiplot)
        self._hiplot_btn.pack(side="left", padx=(8, 0))
        if not _hiplot_available():
            self._hiplot_btn.configure(state="disabled")
            Tooltip(self._hiplot_btn,
                    "Install `parasolpy` and `hiplot` (pip install parasolpy hiplot) "
                    "to enable interactive HiPlot export.")
        else:
            Tooltip(self._hiplot_btn,
                    "Render the latest Pareto front in HiPlot and open it in your browser.")

        self._fig_pareto = Figure(tight_layout=True)
        self._ax_pareto = self._fig_pareto.add_subplot(111)
        canvas1 = FigureCanvasTkAgg(self._fig_pareto, master=t1)
        canvas1.get_tk_widget().grid(row=1, column=0, sticky="nsew")
        tb1 = NavigationToolbar2Tk(canvas1, t1, pack_toolbar=False)
        tb1.grid(row=2, column=0, sticky="ew")
        self._canvas_pareto = canvas1

        # Tab 2 — Progress
        t2 = ttk.Frame(nb)
        nb.add(t2, text="  Progress  ")
        t2.rowconfigure(1, weight=1)
        t2.columnconfigure(0, weight=1)

        bar2 = ttk.Frame(t2)
        bar2.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 0))
        ttk.Label(bar2, text="View:").pack(side="left")
        progress_combo = ttk.Combobox(bar2, textvariable=self._progress_view,
                                      values=["Cartesian", "Parallel axes"],
                                      state="readonly", width=14)
        progress_combo.pack(side="left", padx=(4, 0))
        progress_combo.bind("<<ComboboxSelected>>", self._on_progress_view_change)
        Tooltip(progress_combo, "Switch between Cartesian (line) and parallel-axes (per-objective min/median/max of the latest population) views.")

        self._fig_prog = Figure(tight_layout=True)
        self._ax_prog = self._fig_prog.add_subplot(111)
        canvas2 = FigureCanvasTkAgg(self._fig_prog, master=t2)
        canvas2.get_tk_widget().grid(row=1, column=0, sticky="nsew")
        tb2 = NavigationToolbar2Tk(canvas2, t2, pack_toolbar=False)
        tb2.grid(row=2, column=0, sticky="ew")
        self._canvas_prog = canvas2

        self._draw_placeholders()

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_problem_change(self, _event=None):
        _, accepts_nobjs = PROBLEMS[self._problem_var.get()]
        self._nobjs_spin.configure(state="normal" if accepts_nobjs else "disabled")

    def _run(self):
        prob_name = self._problem_var.get()
        algo_key  = ALGORITHMS[self._algo_var.get()]
        nobjs     = self._nobjs_var.get()
        pop_size  = self._pop_var.get()
        max_nfe   = self._nfe_var.get()
        freq      = self._freq_var.get()

        self._max_nfe = max_nfe
        self._current_nobjs = nobjs
        self._nfe_hist.clear()
        self._size_hist.clear()

        try:
            problem = make_problem(prob_name, nobjs)
        except Exception as e:
            messagebox.showerror("Problem error", str(e))
            return

        self._reset_pareto_axes(nobjs)

        self._run_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._progress["value"] = 0
        self._set_status("Running…", "#1a6bbf")

        self._worker = Worker(self._queue, problem, algo_key, pop_size, max_nfe, freq)
        self._worker.start()
        self.after(100, self._poll)

    def _stop(self):
        if self._worker:
            self._worker.request_stop()
        self._set_status("Stopping…", "#b87a00")

    def _on_close(self):
        if self._worker:
            self._worker.request_stop()
        self.destroy()

    # ── Queue polling ─────────────────────────────────────────────────────────

    def _poll(self):
        try:
            while True:
                msg = self._queue.get_nowait()
                t = msg["t"]
                if t == "update":
                    self._apply_update(msg)
                elif t == "done":
                    self._apply_update(msg)
                    self._on_finish("Done  ✓", "#1e7d1e")
                    return
                elif t == "stopped":
                    self._on_finish("Stopped", "#b87a00")
                    return
                elif t == "error":
                    self._on_finish("Error", "red")
                    messagebox.showerror("Algorithm error",
                                         f"{msg['msg']}\n\n{msg.get('tb', '')}")
                    return
        except queue.Empty:
            pass

        if self._worker and self._worker.is_alive():
            self.after(100, self._poll)

    # ── Update helpers ────────────────────────────────────────────────────────

    def _apply_update(self, msg):
        nfe, result = msg["nfe"], msg["result"]
        self._nfe_hist.append(nfe)
        self._size_hist.append(len(result))
        self._last_result = result
        self._progress["value"] = min(100, 100 * nfe / self._max_nfe)
        self._nfe_label.configure(text=f"NFE: {nfe:,} / {self._max_nfe:,}")
        self._redraw_pareto(result)
        self._redraw_progress()

    def _on_finish(self, text, color):
        self._set_status(text, color)
        self._run_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")

    def _set_status(self, text, color):
        self._status_label.configure(text=text, foreground=color)

    # ── Plot helpers ──────────────────────────────────────────────────────────

    def _draw_placeholders(self):
        for ax, canvas in [(self._ax_pareto, self._canvas_pareto),
                           (self._ax_prog, self._canvas_prog)]:
            ax.clear()
            ax.set_facecolor("#f7f7f7")
            ax.text(0.5, 0.5, "Run an algorithm to see results",
                    ha="center", va="center", color="#aaaaaa", fontsize=11,
                    transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
            canvas.draw()

    def _reset_pareto_axes(self, nobjs):
        self._fig_pareto.clear()
        if self._pareto_view.get() == "Parallel axes":
            self._ax_pareto = self._fig_pareto.add_subplot(111)
        elif nobjs >= 3:
            self._ax_pareto = self._fig_pareto.add_subplot(111, projection="3d")
        else:
            self._ax_pareto = self._fig_pareto.add_subplot(111)
        self._ax_prog.clear()
        self._canvas_pareto.draw()
        self._canvas_prog.draw()

    # ── View-toggle handlers ──────────────────────────────────────────────────

    def _on_pareto_view_change(self, _event=None):
        if self._last_result:
            nobjs = len(self._last_result[0])
            is_3d = getattr(self._ax_pareto, "name", None) == "3d"
            want_3d = self._pareto_view.get() != "Parallel axes" and nobjs >= 3
            if want_3d != is_3d:
                self._reset_pareto_axes(nobjs)
        self._redraw_pareto(self._last_result)

    def _on_progress_view_change(self, _event=None):
        self._redraw_progress()

    # ── Pareto dispatcher + cartesian renderer ────────────────────────────────

    def _redraw_pareto(self, result):
        if self._pareto_view.get() == "Parallel axes":
            self._redraw_pareto_parallel(result)
        else:
            self._redraw_pareto_cartesian(result)

    def _redraw_pareto_cartesian(self, result):
        if not result:
            self._ax_pareto.clear()
            self._canvas_pareto.draw()
            return

        nobjs = len(result[0])
        is_3d = getattr(self._ax_pareto, "name", None) == "3d"
        if (nobjs >= 3) != is_3d:
            self._reset_pareto_axes(nobjs)

        ax = self._ax_pareto
        ax.clear()
        color = "#2577c8"

        if nobjs >= 3:
            ax.scatter([r[0] for r in result],
                       [r[1] for r in result],
                       [r[2] for r in result],
                       s=14, c=color, alpha=0.75, depthshade=True)
            ax.set_xlabel("f₁", labelpad=4)
            ax.set_ylabel("f₂", labelpad=4)
            ax.set_zlabel("f₃", labelpad=4)
            if nobjs > 3:
                ax.set_title(f"Pareto Front (f₁–f₃ shown, {nobjs} total)  ·  {len(result)} solutions")
            else:
                ax.set_title(f"Pareto Front  ·  {len(result)} solutions")
        else:
            ax.scatter([r[0] for r in result],
                       [r[1] for r in result],
                       s=16, c=color, alpha=0.75)
            ax.set_xlabel(f"f{_subscript(1)}")
            ax.set_ylabel(f"f{_subscript(2)}")
            ax.set_title(f"Pareto Front  ·  {len(result)} solutions")
            ax.grid(True, alpha=0.25)

        self._canvas_pareto.draw()

    def _redraw_pareto_parallel(self, result):
        # Ensure axes are 2D for parallel view.
        if getattr(self._ax_pareto, "name", None) == "3d":
            nobjs = len(result[0]) if result else self._current_nobjs
            self._reset_pareto_axes(nobjs)

        ax = self._ax_pareto
        ax.clear()
        if not result:
            self._canvas_pareto.draw()
            return

        # Downsample very large populations for live-update responsiveness.
        if len(result) > 500:
            step = max(1, len(result) // 500)
            rows = result[::step]
        else:
            rows = result

        nobjs = len(rows[0])
        axis_labels = [f"f{_subscript(i + 1)}" for i in range(nobjs)]
        self._draw_parallel_axes(
            ax, rows, axis_labels,
            color_by=[r[0] for r in rows],
            cmap="viridis",
            title=f"Pareto Front (parallel)  ·  {len(result)} solutions",
        )
        self._canvas_pareto.draw()

    # ── Progress dispatcher + renderers ───────────────────────────────────────

    def _redraw_progress(self):
        if self._progress_view.get() == "Parallel axes":
            self._redraw_progress_parallel()
        else:
            self._redraw_progress_cartesian()

    def _redraw_progress_cartesian(self):
        ax = self._ax_prog
        ax.clear()
        ax.plot(self._nfe_hist, self._size_hist,
                color="#2577c8", linewidth=1.8)
        ax.fill_between(self._nfe_hist, self._size_hist,
                        alpha=0.12, color="#2577c8")
        ax.set_xlabel("NFE")
        ax.set_ylabel("Non-dominated solutions")
        ax.set_title("Pareto Front Size")
        ax.grid(True, alpha=0.25)
        self._canvas_prog.draw()

    def _redraw_progress_parallel(self):
        ax = self._ax_prog
        ax.clear()
        if not self._last_result:
            self._canvas_prog.draw()
            return

        result = self._last_result
        nobjs = len(result[0])
        cols = [[r[j] for r in result] for j in range(nobjs)]
        mins = [min(c) for c in cols]
        meds = [statistics.median(c) for c in cols]
        maxs = [max(c) for c in cols]
        axis_labels = [f"f{_subscript(i + 1)}" for i in range(nobjs)]
        colors = ["#2577c8", "#1e7d1e", "#b87a00"]

        nfe_txt = f"{self._nfe_hist[-1]:,}" if self._nfe_hist else "—"
        self._draw_parallel_axes(
            ax, [mins, meds, maxs], axis_labels,
            line_colors=colors,
            alpha=0.9, lw=1.6,
            title=f"Progress (parallel)  ·  NFE {nfe_txt}",
        )
        ax.legend(["min", "median", "max"], loc="upper right")
        self._canvas_prog.draw()

    # ── Parallel-coordinates primitive ────────────────────────────────────────

    def _draw_parallel_axes(self, ax, rows, axis_labels, *, color_by=None,
                            line_colors=None, cmap="viridis", alpha=0.5,
                            lw=0.8, title=None):
        rows = [list(r) for r in rows]
        if not rows:
            return
        n_axes = len(axis_labels)
        cols = [[r[j] for r in rows] for j in range(n_axes)]
        col_min = [min(c) for c in cols]
        col_max = [max(c) for c in cols]
        ranges = [(hi - lo) if (hi - lo) > 1e-12 else 1e-12
                  for lo, hi in zip(col_min, col_max)]

        # Gridlines, ticks, limits.
        for j in range(n_axes):
            ax.axvline(j, color="#cccccc", lw=0.8, zorder=0)
        ax.set_xticks(range(n_axes))
        ax.set_xticklabels(axis_labels)
        ax.set_xlim(-0.2, n_axes - 1 + 0.2)
        ax.set_ylim(-0.05, 1.05)
        ax.set_yticks([])

        # Left-axis min/max annotations (original scale).
        ax.text(-0.12, 0.0, f"{col_min[0]:.3g}", ha="right", va="center",
                fontsize=8, color="#666666")
        ax.text(-0.12, 1.0, f"{col_max[0]:.3g}", ha="right", va="center",
                fontsize=8, color="#666666")

        # Resolve per-line colors.
        if line_colors is not None:
            per_line = list(line_colors)
        elif color_by is not None:
            cb = list(color_by)
            cb_lo, cb_hi = min(cb), max(cb)
            cb_rng = (cb_hi - cb_lo) if (cb_hi - cb_lo) > 1e-12 else 1e-12
            cmap_obj = matplotlib.colormaps[cmap]
            per_line = [cmap_obj((v - cb_lo) / cb_rng) for v in cb]
        else:
            per_line = ["#2577c8"] * len(rows)

        xs = list(range(n_axes))
        for row, col in zip(rows, per_line):
            normalized = [(row[j] - col_min[j]) / ranges[j] for j in range(n_axes)]
            ax.plot(xs, normalized, color=col, alpha=alpha, lw=lw)

        if title:
            ax.set_title(title)

    # ── HiPlot export ─────────────────────────────────────────────────────────

    def _open_in_hiplot(self):
        """Render the latest Pareto front in HiPlot and open it in the browser.

        Assumes minimization for all objectives (consistent with Plotypus's
        benchmark registry). If a future GUI exposes maximization problems,
        flip the corresponding entries in `obj_directions` below.
        """
        if not self._last_result:
            messagebox.showinfo("HiPlot export", "Run an algorithm first.")
            return
        try:
            import pandas as pd
            import parasolpy
            nobjs = len(self._last_result[0])
            cols = [f"f{i + 1}" for i in range(nobjs)]
            df = pd.DataFrame(self._last_result, columns=cols)
            exp = parasolpy.parallel_plot_hp(
                df,
                obj_names=cols,
                obj_directions=["minimize"] * nobjs,
            )
            tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False)
            tmp.close()
            exp.to_html(tmp.name)
            webbrowser.open(f"file:///{tmp.name}")
        except Exception as e:
            messagebox.showerror("HiPlot export failed", str(e))


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
