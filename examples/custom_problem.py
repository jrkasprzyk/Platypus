from plotypus import NSGAII, Problem, Real

# Function-based: pass a plain function to problem.function
def schaffer(x):
    return [x[0]**2, (x[0]-2)**2]

problem = Problem(1, 2)
problem.types[:] = Real(-10, 10)
problem.function = schaffer

algorithm = NSGAII(problem)
algorithm.run(10000)

# Class-based: subclass Problem and override evaluate()
class Schaffer(Problem):
    def __init__(self):
        super().__init__(1, 2)
        self.types[:] = Real(-10, 10)

    def evaluate(self, solution):
        x = solution.variables[0]
        solution.objectives[:] = [x**2, (x - 2)**2]

algorithm = NSGAII(Schaffer())
algorithm.run(10000)

# Schaffer is also available as: from plotypus.problems import Schaffer
