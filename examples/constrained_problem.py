from plotypus import NSGAII, Problem, Real

# Function-based constrained problem: return (objectives, constraints)
def belegundu(vars):
    x, y = vars[0], vars[1]
    return [-2*x + y, 2*x + y], [-x + y - 1, x + y - 7]

problem = Problem(2, 2, 2)
problem.types[:] = [Real(0, 5), Real(0, 3)]
problem.constraints[:] = "<=0"
problem.function = belegundu

algorithm = NSGAII(problem)
algorithm.run(10000)

# Class-based constrained problem
class Belegundu(Problem):
    def __init__(self):
        super().__init__(2, 2, 2)
        self.types[:] = [Real(0, 5), Real(0, 3)]
        self.constraints[:] = "<=0"

    def evaluate(self, solution):
        x = solution.variables[0]
        y = solution.variables[1]
        solution.objectives[:] = [-2*x + y, 2*x + y]
        solution.constraints[:] = [-x + y - 1, x + y - 7]

algorithm = NSGAII(Belegundu())
algorithm.run(10000)

# Belegundu is also available as: from plotypus.problems import Belegundu
