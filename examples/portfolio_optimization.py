from plotypus import NSGAII, nondominated
from plotypus.problems import PortfolioOptimization

ASSETS  = ["Tech", "Health", "Energy", "Finance", "Consumer", "Utilities"]
RETURNS = [0.15,   0.10,    0.08,     0.09,      0.07,       0.05]
VOLS    = [0.25,   0.15,    0.20,     0.18,      0.12,       0.08]
CORR = [
    [ 1.00,  0.30,  0.10,  0.40,  0.35, -0.10],
    [ 0.30,  1.00,  0.05,  0.25,  0.40,  0.15],
    [ 0.10,  0.05,  1.00,  0.20,  0.05,  0.10],
    [ 0.40,  0.25,  0.20,  1.00,  0.30,  0.05],
    [ 0.35,  0.40,  0.05,  0.30,  1.00,  0.20],
    [-0.10,  0.15,  0.10,  0.05,  0.20,  1.00],
]

problem = PortfolioOptimization(ASSETS, RETURNS, VOLS, CORR)
algorithm = NSGAII(problem, population_size=200)
algorithm.run(100_000)

front = nondominated(algorithm.result)
print(f"Pareto front: {len(front)} solutions\n")
print(f"{'Variance':>10} {'Return':>8} {'HHI':>6}   Weights (%)")

N = len(ASSETS)
for s in sorted(front, key=lambda x: x.objectives[0])[:12]:
    raw = s.variables[:]
    total = sum(raw)
    w = [r / total for r in raw] if total > 1e-9 else [1/N] * N
    wstr = "  ".join(f"{ASSETS[i][0]}:{w[i]*100:4.1f}%" for i in range(N))
    print(f"{s.objectives[0]:10.5f} {s.objectives[1]:8.4f} {s.objectives[2]:6.4f}   {wstr}")
