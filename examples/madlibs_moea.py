"""
Mad Libs MOEA — human-in-the-loop funniness optimizer.
Decision variables: word index for each story blank.
Objective: maximize user-rated funniness (1-10).
User's original answers are index 0 in each candidate list.
"""

import argparse

from plotypus import Direction, Integer, NSGAII, Problem

STORY = (
    "The {time_of_day} everything changed started like any other day at the local {place}.\n"
    "{celebrity} had just finished {verb_ing} when a {adjective} sound echoed through the halls.\n"
    "'Great {exclamation}!' someone screamed. Before anyone could react, {animals}\n"
    "stampeded through the entrance — each one wearing a tiny tuxedo.\n"
    "Witnesses reported that {celebrity} remained completely calm, adjusted their collar, and said:\n"
    "'I've seen more {adjective} things than this.' They had not."
)

# Index 0 in each list = the user's original answer
CANDIDATES = {
    "time_of_day": [
        "early morning", "3 AM", "high noon", "naptime",
        "the crack of dawn", "dusk", "2:47 PM", "the precise moment of sunset",
    ],
    "place": [
        "law library", "DMV", "Chuck E. Cheese", "Applebee's",
        "a funeral home", "Costco", "a laser tag arena", "a chiropractor's office",
    ],
    "celebrity": [
        "Wilford Brimley", "Nicolas Cage", "Dwayne Johnson", "Keanu Reeves",
        "Celine Dion", "Jeff Bezos", "Bill Nye", "Gordon Ramsay",
    ],
    "verb_ing": [
        "kung fu fighting", "aggressively napping", "interpretive dancing",
        "narrating their own life", "dramatically sighing",
        "power walking", "yodeling", "eating a sandwich",
    ],
    "adjective": [
        "fat", "moist", "suspiciously formal", "biblically accurate",
        "unnecessarily loud", "aggressively beige", "structurally unsound", "legally distinct",
    ],
    "exclamation": [
        "fiddlesticks", "Wisconsin", "Linguistics", "Banana",
        "Tambourine", "Mortgage", "Bureaucracy", "Lasagna",
    ],
    "animals": [
        "a murder of crows", "47 capybaras", "a dozen emus", "3 raccoons",
        "99 geese", "12 axolotls", "666 flamingos", "2 wombats",
    ],
}

KEYS  = list(CANDIDATES.keys())
SIZES = [len(CANDIDATES[k]) for k in KEYS]

_cache: dict = {}

RESET  = "\033[0m"
YELLOW = "\033[93m"  # word changed vs previous story
DIM    = "\033[2m"   # word unchanged
CYAN   = "\033[96m"  # generation banner


def _colorize(words, current_key, prev_key):
    story = STORY
    for i, k in enumerate(KEYS):
        word = words[k]
        color = YELLOW if (prev_key is None or prev_key[i] != current_key[i]) else DIM
        story = story.replace(f"{{{k}}}", f"{color}{word}{RESET}")
    return story


class MadLibsFunniness(Problem):

    def __init__(self, pop_size):
        super().__init__(len(KEYS), 1)
        self._pop_size = pop_size
        self._eval_count = 0
        self._prev_key = None
        self._generation = 0
        for i, sz in enumerate(SIZES):
            self.types[i] = Integer(0, sz - 1)
        self.directions[0] = Direction.MAXIMIZE

    def evaluate(self, solution):
        self._eval_count += 1

        if self._eval_count > self._pop_size and (self._eval_count - 1) % self._pop_size == 0:
            self._generation += 1
            print(f"\n{CYAN}--- Generation {self._generation} ---{RESET}")

        key = tuple(int(v) for v in solution.variables[:])

        if key in _cache:
            solution.objectives[0] = _cache[key]
            return

        words = {KEYS[i]: CANDIDATES[KEYS[i]][key[i]] for i in range(len(KEYS))}
        filled = _colorize(words, key, self._prev_key)

        print("\n" + "-" * 64)
        print(filled)
        print("-" * 64)
        while True:
            try:
                score = float(input("  Funniness (1-10): "))
                if 1 <= score <= 10:
                    break
            except ValueError:
                pass
            print("  Enter a number 1-10.")

        self._prev_key = key
        _cache[key] = score
        solution.objectives[0] = score


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mad Libs MOEA funniness optimizer")
    parser.add_argument("--evals", type=int, default=12,
                        help="total function evaluations (default: 12)")
    parser.add_argument("--pop-size", type=int, default=4,
                        help="NSGA-II population size (default: 4)")
    args = parser.parse_args()

    print("MOEA optimizing for maximum funniness.")
    print(f"Running {args.evals} evals, pop size {args.pop_size}.")
    print("Rate each story 1-10. Duplicate combos won't re-prompt.")
    print(f"{YELLOW}Yellow words{RESET} = changed from last story. {DIM}Dim{RESET} = same.\n")
    print("(Your original answers = index 0 in each candidate list)\n")

    problem   = MadLibsFunniness(args.pop_size)
    algorithm = NSGAII(problem, population_size=args.pop_size)
    algorithm.run(args.evals)

    best = max(algorithm.result, key=lambda s: s.objectives[0])
    key  = tuple(problem.types[i].decode(best.variables[i]) for i in range(len(KEYS)))
    words = {KEYS[i]: CANDIDATES[KEYS[i]][key[i]] for i in range(len(KEYS))}

    print("\n" + "=" * 64)
    print(f"MOEA CHAMPION  (your score: {best.objectives[0]:.1f}/10)")
    print("=" * 64)
    print(STORY.format(**words))
    print("\nWinning words:")
    for k in KEYS:
        v      = words[k]
        orig   = CANDIDATES[k][0]
        marker = "  ← your original" if v == orig else ""
        print(f"  {k:12s}: {v}{marker}")

    print(f"\nTotal unique combos rated: {len(_cache)}")
