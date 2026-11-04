"""8-puzzle solver using heuristic search.

Usage:
    python eight_puzzle.py solve "2 8 3 1 6 4 7 0 5" [-a astar] [-H manhattan]
    python eight_puzzle.py solve --random
    python eight_puzzle.py solve --level hard            # animated; --delay 0.2, --quiet
    python eight_puzzle.py compare [-n 50] [--seed 1]

States are 9-tuples read row by row; 0 is the blank.
"""
import argparse
import heapq
import itertools
import random
import sys
import time
from collections import deque

GOAL = (1, 2, 3, 4, 5, 6, 7, 8, 0)
MOVES = {"Up": -3, "Down": 3, "Left": -1, "Right": 1}


# ---------- puzzle helpers ----------

def is_solvable(state, goal=GOAL):
    """Solvable iff the inversion parity of start and goal match (odd-width board)."""
    def inversions(s):
        t = [x for x in s if x]
        return sum(a > b for a, b in itertools.combinations(t, 2))
    return inversions(state) % 2 == inversions(goal) % 2


def neighbors(state):
    """Yield (move_name, next_state) for every legal move of the blank."""
    b = state.index(0)
    r, c = divmod(b, 3)
    for name, d in MOVES.items():
        if (name == "Up" and r == 0) or (name == "Down" and r == 2):
            continue
        if (name == "Left" and c == 0) or (name == "Right" and c == 2):
            continue
        s = list(state)
        s[b], s[b + d] = s[b + d], s[b]
        yield name, tuple(s)


def random_state(rng):
    while True:
        s = list(GOAL)
        rng.shuffle(s)
        s = tuple(s)
        if is_solvable(s):
            return s


LEVELS = {"easy": 6, "medium": 14, "hard": 26}
# Known worst-case boards: 31 moves is the maximum for the 8-puzzle.
HARDEST = [(8, 6, 7, 2, 5, 4, 3, 0, 1), (6, 4, 7, 8, 5, 0, 3, 2, 1)]


def scramble_state(moves, rng):
    """Random walk of `moves` legal moves from the goal (never undoing the last move).

    Always solvable, and difficulty is controlled by `moves`.
    """
    s, prev = GOAL, None
    for _ in range(moves):
        options = [n for _, n in neighbors(s) if n != prev]
        prev, s = s, rng.choice(options)
    return s


def level_state(level, rng):
    """Board for a difficulty level: easy / medium / hard / hardest / random."""
    if level == "random":
        return random_state(rng)
    if level == "hardest":
        return rng.choice(HARDEST)
    return scramble_state(LEVELS[level], rng)


def show(state):
    return "\n".join(" ".join(str(x) if x else "_" for x in state[i:i + 3]) for i in (0, 3, 6))


# ---------- heuristics ----------

def h_misplaced(state):
    return sum(1 for i, t in enumerate(state) if t and t != GOAL[i])


def h_manhattan(state):
    total = 0
    for i, t in enumerate(state):
        if t:
            g = t - 1
            total += abs(i // 3 - g // 3) + abs(i % 3 - g % 3)
    return total


def h_linear_conflict(state):
    """Manhattan + 2 for each pair of tiles in their goal row/col but in reversed order."""
    extra = 0
    for r in range(3):  # rows
        tiles = [t for t in state[r * 3:r * 3 + 3] if t and (t - 1) // 3 == r]
        extra += 2 * sum(a > b for a, b in itertools.combinations(tiles, 2))
    for c in range(3):  # columns
        tiles = [t for t in state[c::3] if t and (t - 1) % 3 == c]
        extra += 2 * sum(a > b for a, b in itertools.combinations(tiles, 2))
    return h_manhattan(state) + extra


HEURISTICS = {
    "misplaced": h_misplaced,
    "manhattan": h_manhattan,
    "linear_conflict": h_linear_conflict,
}


# ---------- search ----------

def bfs(start):
    if start == GOAL:
        return [], 0
    frontier = deque([start])
    parent = {start: None}
    expanded = 0
    while frontier:
        s = frontier.popleft()
        expanded += 1
        for name, n in neighbors(s):
            if n not in parent:
                parent[n] = (s, name)
                if n == GOAL:
                    return _path(parent, n), expanded
                frontier.append(n)
    return None, expanded


def best_first(start, h, greedy=False):
    """A* (f = g + h) or Greedy Best-First (f = h). Returns (moves, expanded)."""
    tie = itertools.count()
    open_heap = [(h(start), next(tie), 0, start)]
    parent = {start: None}
    best_g = {start: 0}
    expanded = 0
    while open_heap:
        _, _, g, s = heapq.heappop(open_heap)
        if g > best_g[s]:
            continue  # stale entry
        if s == GOAL:
            return _path(parent, s), expanded
        expanded += 1
        for name, n in neighbors(s):
            ng = g + 1
            if ng < best_g.get(n, float("inf")):
                best_g[n] = ng
                parent[n] = (s, name)
                f = h(n) if greedy else ng + h(n)
                heapq.heappush(open_heap, (f, next(tie), ng, n))
    return None, expanded


def _path(parent, s):
    moves = []
    while parent[s] is not None:
        s, m = parent[s]
        moves.append(m)
    return moves[::-1]


def run(algo, heur, start):
    if algo == "bfs":
        return bfs(start)
    return best_first(start, HEURISTICS[heur], greedy=(algo == "greedy"))


# ---------- CLI ----------

def animate(start, moves, delay):
    """Show the solution board by board; redraws in place when run in a terminal."""
    in_place = sys.stdout.isatty() and delay > 0
    total = len(moves)

    def frame(label, s):
        if in_place:
            print(label.ljust(28))
            print(show(s))
        else:
            print(label + "\n" + show(s) + "\n")

    s = start
    frame(f"Step 0/{total}: start", s)
    for i, m in enumerate(moves, 1):
        time.sleep(delay)
        s = dict(neighbors(s))[m]
        if in_place:
            sys.stdout.write("\033[4A")  # move cursor up over the previous frame
        frame(f"Step {i}/{total}: blank moves {m}", s)


def cmd_solve(args):
    rng = random.Random(args.seed)
    if args.level:
        start = level_state(args.level, rng)
    elif args.random:
        start = random_state(rng)
    else:
        start = tuple(int(x) for x in args.state.split())
        if sorted(start) != list(range(9)):
            raise SystemExit("State must contain each of 0-8 exactly once.")
    if not is_solvable(start):
        raise SystemExit("This puzzle is unsolvable (odd inversion parity).")
    print("Start:\n" + show(start))
    t = time.perf_counter()
    moves, expanded = run(args.algo, args.heuristic, start)
    dt = time.perf_counter() - t
    print(f"\n{args.algo}" + (f" + {args.heuristic}" if args.algo != "bfs" else ""))
    print(f"Solved in {len(moves)} moves, {expanded} nodes expanded, {dt * 1000:.1f} ms")
    print("Moves:", " ".join(moves) or "(already solved)")
    if moves and not args.quiet:
        print()
        animate(start, moves, args.delay)


def cmd_compare(args):
    rng = random.Random(args.seed)
    puzzles = [random_state(rng) for _ in range(args.n)]
    configs = [("bfs", None)] + [("astar", h) for h in HEURISTICS] + [("greedy", "manhattan")]
    print(f"{args.n} random solvable puzzles (seed={args.seed})\n")
    print(f"{'algorithm':<26}{'avg expanded':>14}{'avg length':>12}{'avg ms':>10}{'optimal':>9}")
    optimal_len = None
    for algo, heur in configs:
        exp = 0
        t = time.perf_counter()
        lens = []
        for p in puzzles:
            moves, e = run(algo, heur, p)
            exp += e
            lens.append(len(moves))
        ms = (time.perf_counter() - t) * 1000 / args.n
        if optimal_len is None:
            optimal_len = lens  # BFS is optimal
        opt = sum(a == b for a, b in zip(lens, optimal_len))
        name = algo + (f" + {heur}" if heur else "")
        print(f"{name:<26}{exp / args.n:>14.1f}{sum(lens) / args.n:>12.2f}{ms:>10.1f}{opt:>5}/{args.n}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("solve", help="solve one puzzle")
    s.add_argument("state", nargs="?", help='9 numbers, e.g. "2 8 3 1 6 4 7 0 5"')
    s.add_argument("--random", action="store_true", help="fully random solvable board")
    s.add_argument("--level", choices=["easy", "medium", "hard", "hardest"],
                   help="auto-generate a board of the given difficulty")
    s.add_argument("--seed", type=int)
    s.add_argument("-a", "--algo", choices=["astar", "greedy", "bfs"], default="astar")
    s.add_argument("-H", "--heuristic", choices=list(HEURISTICS), default="manhattan")
    s.add_argument("--delay", type=float, default=0.5,
                   help="seconds between animation frames (default 0.5; 0 = print instantly)")
    s.add_argument("--quiet", action="store_true", help="skip the step-by-step board display")
    s.set_defaults(fn=cmd_solve)

    c = sub.add_parser("compare", help="benchmark algorithms/heuristics")
    c.add_argument("-n", type=int, default=50)
    c.add_argument("--seed", type=int, default=1)
    c.set_defaults(fn=cmd_compare)

    args = p.parse_args()
    if args.cmd == "solve" and not (args.state or args.random or args.level):
        p.error("give a state, --random, or --level")
    args.fn(args)


if __name__ == "__main__":
    main()
