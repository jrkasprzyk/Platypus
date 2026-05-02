#!/usr/bin/env python3
"""Plotypus Explorer — GUI for multiobjective optimization."""

import math
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from plotypus import (
    EpsMOEA, EpsNSGAII, GDE3, IBEA, MOEAD, NSGAII, NSGAIII, OMOPSO, SMPSO, SPEA2,
    DTLZ1, DTLZ2, DTLZ3, DTLZ4, DTLZ7,
    ZDT1, ZDT2, ZDT3, ZDT4, ZDT6,
    WFG1, WFG2, WFG3, WFG4, WFG5, WFG6, WFG7, WFG8, WFG9,
)

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
        self._stop = threading.Event()

    def request_stop(self):
        self._stop.set()

    def run(self):
        try:
            algo = make_algorithm(self.algo_key, self.problem, self.pop_size)
            state = {"last": 0}

            def cb(a):
                if self._stop.is_set():
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

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── UI construction ───────────────────────────────────────────────────────

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

        ttk.Label(side, text="Objectives").grid(row=r, column=0, sticky="w")
        self._nobjs_var = tk.IntVar(value=2)
        self._nobjs_spin = ttk.Spinbox(side, from_=2, to=8,
                                       textvariable=self._nobjs_var, width=5)
        self._nobjs_spin.grid(row=r, column=1, pady=2, padx=(6, 0), sticky="e"); r += 1

        ttk.Separator(side, orient="horizontal").grid(
            row=r, column=0, columnspan=2, sticky="ew", pady=8); r += 1

        # ── Algorithm ──
        ttk.Label(side, text="Algorithm", font=("Segoe UI", 9, "bold")).grid(
            row=r, column=0, columnspan=2, sticky="w", pady=(0, 2)); r += 1

        ttk.Label(side, text="Algorithm").grid(row=r, column=0, sticky="w")
        self._algo_var = tk.StringVar(value="NSGA-II")
        ttk.Combobox(side, textvariable=self._algo_var,
                     values=list(ALGORITHMS), state="readonly", width=10).grid(
            row=r, column=1, pady=2, padx=(6, 0), sticky="e"); r += 1

        ttk.Label(side, text="Pop size").grid(row=r, column=0, sticky="w")
        self._pop_var = tk.IntVar(value=100)
        ttk.Spinbox(side, from_=10, to=2000, increment=10,
                    textvariable=self._pop_var, width=7).grid(
            row=r, column=1, pady=2, padx=(6, 0), sticky="e"); r += 1

        ttk.Label(side, text="Max NFE").grid(row=r, column=0, sticky="w")
        self._nfe_var = tk.IntVar(value=10000)
        ttk.Entry(side, textvariable=self._nfe_var, width=8).grid(
            row=r, column=1, pady=2, padx=(6, 0), sticky="e"); r += 1

        ttk.Label(side, text="Update every").grid(row=r, column=0, sticky="w")
        self._freq_var = tk.IntVar(value=500)
        ttk.Spinbox(side, from_=50, to=5000, increment=50,
                    textvariable=self._freq_var, width=7).grid(
            row=r, column=1, pady=2, padx=(6, 0), sticky="e"); r += 1

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
        t1.rowconfigure(0, weight=1)
        t1.columnconfigure(0, weight=1)

        self._fig_pareto = Figure(tight_layout=True)
        self._ax_pareto = self._fig_pareto.add_subplot(111)
        canvas1 = FigureCanvasTkAgg(self._fig_pareto, master=t1)
        canvas1.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        tb1 = NavigationToolbar2Tk(canvas1, t1, pack_toolbar=False)
        tb1.grid(row=1, column=0, sticky="ew")
        self._canvas_pareto = canvas1

        # Tab 2 — Progress
        t2 = ttk.Frame(nb)
        nb.add(t2, text="  Progress  ")
        t2.rowconfigure(0, weight=1)
        t2.columnconfigure(0, weight=1)

        self._fig_prog = Figure(tight_layout=True)
        self._ax_prog = self._fig_prog.add_subplot(111)
        canvas2 = FigureCanvasTkAgg(self._fig_prog, master=t2)
        canvas2.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        tb2 = NavigationToolbar2Tk(canvas2, t2, pack_toolbar=False)
        tb2.grid(row=1, column=0, sticky="ew")
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
        if nobjs >= 3:
            self._ax_pareto = self._fig_pareto.add_subplot(111, projection="3d")
        else:
            self._ax_pareto = self._fig_pareto.add_subplot(111)
        self._ax_prog.clear()
        self._canvas_pareto.draw()
        self._canvas_prog.draw()

    def _redraw_pareto(self, result):
        ax = self._ax_pareto
        ax.clear()

        if not result:
            self._canvas_pareto.draw()
            return

        nobjs = len(result[0])
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
            ax.set_xlabel("f₁")
            ax.set_ylabel("f₂")
            ax.set_title(f"Pareto Front  ·  {len(result)} solutions")
            ax.grid(True, alpha=0.25)

        self._canvas_pareto.draw()

    def _redraw_progress(self):
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


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
