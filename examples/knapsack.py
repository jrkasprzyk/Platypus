from plotypus import GeneticAlgorithm, nondominated, unique
from plotypus.problems import Knapsack

# This simple instance has an optimal value of 15 when picking items 1 and 4.
weights = [2, 3, 6, 7, 5, 9, 4]
profits = [6, 5, 8, 9, 6, 7, 3]

algorithm = GeneticAlgorithm(Knapsack(weights, profits, capacity=9))
algorithm.run(10000)

for solution in unique(nondominated(algorithm.result)):
    print(solution.variables, solution.objectives)
