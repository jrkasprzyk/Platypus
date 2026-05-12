===============
Getting Started
===============

Installing Plotypus
-------------------

Plotypus uses `Poetry <https://python-poetry.org/>`_ as its build backend and
dependency manager.  If you don't have Poetry installed, follow the
`installation instructions <https://python-poetry.org/docs/#installation>`_
first.

Clone the repository and install:

::

   git clone https://github.com/jrkasprzyk/Plotypus.git
   cd Plotypus
   poetry install

This creates a Poetry-managed virtual environment with Plotypus installed in
editable mode and all dependencies resolved.

To include the optional MPI / parallel-evaluation extras:

::

   poetry install --extras full

Run Plotypus scripts inside the environment with ``poetry run``:

::

   poetry run python my_script.py

Or activate the environment once per terminal session.  Poetry 2.0+ prints the
activation command for your shell via:

::

   poetry env activate

Copy and run the printed command to activate.  (Earlier versions of Poetry
provided ``poetry shell`` directly; in 2.0+ this has been moved to the
optional ``poetry-plugin-shell`` plugin.)

To build a distributable wheel:

::

   poetry build

A Simple Example
----------------

As an initial example, we will solve the well-known two objective DTLZ2 problem
using the NSGA-II algorithm:

.. literalinclude:: ../examples/print_results.py
   :language: python

The output shows on each line the objectives for a Pareto optimal solution:

.. code::

   [1.00289403128, 6.63772921439e-05]
   [0.000320076737668, 1.00499316652]
   [1.00289403128, 6.63772921439e-05]
   [0.705383878891, 0.712701387377]
   [0.961083112366, 0.285860932437]
   [0.729124908607, 0.688608373855]
   ...

Plotypus includes *matplotlib* as a core dependency, so we can plot the
results directly.  Running the following code

.. literalinclude:: ../examples/plot_results.py
   :language: python

produce a plot similar to:

.. image:: images/figure_1.png
   :scale: 60 %
   :alt: Pareto front for the DTLZ2 problem
   :align: center

Note that we did not need to specify many settings when constructing NSGA-II.
For any options not specified by the user, Plotypus supplies the appropriate
settings using best practices.  In this example, Plotypus inspected the
problem definition to determine that the DTLZ2 problem consists of real-valued
decision variables and selected the Simulated Binary Crossover (SBX) and
Polynomial Mutation (PM) operators.  One can easily switch to using different
operators, such as Parent-Centric Crossover (PCX):

.. literalinclude:: ../examples/customize_variator.py
   :language: python

Defining Problems
-----------------

Plotypus provides three ways to define a problem.  Choosing the right one
matters: each suits a different stage of work, and mixing them up is a common
source of confusion for new users.

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Approach
     - Use when
     - Example
   * - **Built-in**
     - The problem already ships with Plotypus.  Don't reinvent standard
       benchmark problems.
     - ``from plotypus.problems import Schaffer``
   * - **Function-based**
     - Quick prototyping, single-use, no state to carry between evaluations.
       Fastest to write.
     - ``problem.function = my_func``
   * - **Class-based**
     - Reusable problem you (or others) will instantiate many times, or you
       need to store state, parameters, or helper methods.
     - ``class MyProblem(Problem): ...``

All three center on the ``Problem`` class.  In every case you must declare:

1. The number of decision variables
2. The number of objectives
3. The type of each decision variable (e.g. ``Real(-10, 10)``)
4. The evaluation logic (function returning a list of objective values)

The examples below all solve the same bi-objective Schaffer problem:

.. math::

    \text{minimize } (x^2, (x-2)^2) \text{ for } x \in [-10, 10]

Built-in
~~~~~~~~

Before writing your own, check ``plotypus.problems`` for a built-in.  Standard
benchmark problems (Schaffer, DTLZ family, ZDT family, Belegundu, and many
others) are already implemented:

.. code:: python

   from plotypus import NSGAII
   from plotypus.problems import Schaffer

   algorithm = NSGAII(Schaffer())
   algorithm.run(10000)

This is the version students and reviewers should reach for first.  Reproducing
a standard benchmark by hand is a common source of subtle bugs (wrong bounds,
wrong objective signs).

Function-based
~~~~~~~~~~~~~~

For a one-off problem, define a plain function and attach it to a ``Problem``
instance via the ``function`` attribute:

.. code:: python

   from plotypus import NSGAII, Problem, Real

   def schaffer(x):
       return [x[0]**2, (x[0] - 2)**2]

   problem = Problem(1, 2)
   problem.types[:] = Real(-10, 10)
   problem.function = schaffer

   algorithm = NSGAII(problem)
   algorithm.run(10000)

The function takes a list of decision variables and returns a list of objective
values.  ``Problem(1, 2)`` declares one decision variable and two objectives.

**Tip:** The notation ``problem.types[:]`` is a shorthand way to assign all
decision variables to the same type, using Python's slice notation.  You can
also assign a single type, ``problem.types[0]``, or any subset,
``problem.types[1:]``.

This approach is convenient but has limits: the problem is not reusable without
re-running the setup, and you cannot easily share parameters between
construction and evaluation.

Class-based
~~~~~~~~~~~

For a reusable problem, subclass ``Problem``.  Put the type declarations in
``__init__`` and the evaluation logic in ``evaluate``:

.. code:: python

   from plotypus import NSGAII, Problem, Real

   class Schaffer(Problem):
       def __init__(self):
           super().__init__(1, 2)
           self.types[:] = Real(-10, 10)

       def evaluate(self, solution):
           x = solution.variables[0]
           solution.objectives[:] = [x**2, (x - 2)**2]

   algorithm = NSGAII(Schaffer())
   algorithm.run(10000)

Two differences from the function-based form:

- ``evaluate`` receives a ``solution`` object rather than a bare list, and
  writes the results to ``solution.objectives[:]`` instead of returning them.
- All setup lives in ``__init__``, so the problem can be instantiated repeatedly
  with no setup code at the call site.

This is the form you'll see in ``plotypus.problems`` and the form to use when
publishing a problem for others to reuse.

Adding Constraints
~~~~~~~~~~~~~~~~~~

Constraints are not a separate kind of problem — they are two extra pieces of
information on the same ``Problem`` class.  To add constraints you must:

1. Pass the number of constraints as the third argument to ``Problem(...)``
2. Set ``problem.constraints[:]`` to the feasibility criterion (e.g. ``"<=0"``)
3. Return (or assign) constraint values alongside objectives

To demonstrate, we use the Belegundu problem:

.. math::

    \text{minimize } (-2x+y, 2x+y) \text{ subject to } y-x \leq 1 \text{ and } x+y \leq 7

We first simplify the constraints by moving the constant to the left of the
inequality:

.. math::

    \text{minimize } (-2x+y, 2x+y) \text{ subject to } y-x-1 \leq 0 \text{ and } x+y-7 \leq 0

Function-based with constraints:

.. code:: python

   from plotypus import NSGAII, Problem, Real

   def belegundu(vars):
       x, y = vars[0], vars[1]
       return [-2*x + y, 2*x + y], [-x + y - 1, x + y - 7]

   problem = Problem(2, 2, 2)
   problem.types[:] = [Real(0, 5), Real(0, 3)]
   problem.constraints[:] = "<=0"
   problem.function = belegundu

   algorithm = NSGAII(problem)
   algorithm.run(10000)

``Problem(2, 2, 2)`` declares two decision variables, two objectives, and two
constraints.  The function returns a tuple ``(objectives, constraints)`` — two
lists.

The feasibility criterion ``"<=0"`` means a solution is feasible when every
constraint value is less than or equal to zero.  Plotypus accepts other
operators too: ``">=0"``, ``"==0"``, ``"!=5"``.

Class-based with constraints:

.. code:: python

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

Same delta as the unconstrained case: ``evaluate`` writes ``solution.constraints[:]``
instead of returning them.

Filtering Results
~~~~~~~~~~~~~~~~~

When solving constrained problems, the final population may contain infeasible
solutions (especially if the evaluation budget was small, e.g.
``algorithm.run(100)``).  Filter them out:

.. code:: python

   feasible_solutions = [s for s in algorithm.result if s.feasible]

You can also take only non-dominated solutions:

.. code:: python

   nondominated_solutions = nondominated(algorithm.result)

Optimization Direction
~~~~~~~~~~~~~~~~~~~~~~

Plotypus minimizes objectives by default.  Override per-objective via the
``directions`` attribute:

.. code:: python

   problem.directions[:] = Direction.MAXIMIZE
