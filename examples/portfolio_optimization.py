"""
Portfolio Optimization — 3-objective MOEA test problem.

Optimize allocation across 6 synthetic sector ETFs balancing:
  f1: minimize portfolio variance (risk)
  f2: maximize expected annual return
  f3: minimize concentration (Herfindahl-Hirschman index)

Variables: 6 weights in [0,1], normalized to sum=1 inside evaluate().
This avoids an equality constraint while keeping the search space unconstrained.
"""

from plotypus import Direction, NSGAII, Problem, Real, nondominated

ASSETS  = ["Tech", "Health", "Energy", "Finance", "Consumer", "Utilities"]
RETURNS = [0.15,   0.10,    0.08,     0.09,      0.07,       0.05]
VOLS    = [0.25,   0.15,    0.20,     0.18,      0.12,       0.08]

# Correlation matrix — utilities hedge tech (negative corr), energy is low-corr
CORR = [
    [ 1.00,  0.30,  0.10,  0.40,  0.35, -0.10],
    [ 0.30,  1.00,  0.05,  0.25,  0.40,  0.15],
    [ 0.10,  0.05,  1.00,  0.20,  0.05,  0.10],
    [ 0.40,  0.25,  0.20,  1.00,  0.30,  0.05],
    [ 0.35,  0.40,  0.05,  0.30,  1.00,  0.20],
    [-0.10,  0.15,  0.10,  0.05,  0.20,  1.00],
]

N   = len(ASSETS)
COV = [[CORR[i][j] * VOLS[i] * VOLS[j] for j in range(N)] for i in range(N)]


class PortfolioOptimization(Problem):

    def __init__(self):
        super().__init__(N, 3)
        self.types[:]     = Real(0, 1)
        self.directions[1] = Direction.MAXIMIZE  # maximize return

    def evaluate(self, solution):
        raw   = solution.variables[:]
        total = sum(raw)
        w     = [r / total for r in raw] if total > 1e-9 else [1/N] * N

        variance = sum(w[i] * w[j] * COV[i][j]
                       for i in range(N) for j in range(N))
        ret      = sum(w[i] * RETURNS[i] for i in range(N))
        hhi      = sum(wi**2 for wi in w)          # 1/N (max diverse) → 1.0 (all-in)

        solution.objectives[:] = [variance, ret, hhi]


if __name__ == "__main__":
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

    algorithm = NSGAII(PortfolioOptimization(), population_size=200)
    algorithm.run(100_000)

    front = nondominated(algorithm.result)
    print(f"Pareto front: {len(front)} solutions\n")
    print(f"{'Variance':>10} {'Return':>8} {'HHI':>6}   Weights (%)")

    raw_all = solution.variables[:]  # satisfy linter — overwritten below
    for s in sorted(front, key=lambda x: x.objectives[0])[:12]:
        raw = s.variables[:]
        total = sum(raw)
        w = [r / total for r in raw] if total > 1e-9 else [1/N] * N
        wstr = "  ".join(f"{ASSETS[i][0]}:{w[i]*100:4.1f}%" for i in range(N))
        print(f"{s.objectives[0]:10.5f} {s.objectives[1]:8.4f} {s.objectives[2]:6.4f}   {wstr}")

    # 3D Pareto surface: risk vs return vs concentration
    fig = plt.figure(figsize=(10, 7))
    ax  = fig.add_subplot(111, projection="3d")
    xs  = [s.objectives[0] for s in front]   # variance
    ys  = [s.objectives[1] for s in front]   # return
    zs  = [s.objectives[2] for s in front]   # HHI
    sc  = ax.scatter(xs, ys, zs, c=ys, cmap="viridis", s=10)
    ax.set_xlabel("Portfolio Variance (risk)")
    ax.set_ylabel("Expected Return")
    ax.set_zlabel("Concentration (HHI)")
    ax.set_title("3-Objective Portfolio Pareto Front")
    plt.colorbar(sc, label="Return", shrink=0.5)
    plt.tight_layout()
    plt.show()
