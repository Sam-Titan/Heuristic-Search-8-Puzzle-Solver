# 8-Puzzle Solver (Heuristic Search)

A small project that solves the classic 8-puzzle with heuristic search and compares how
different algorithms and heuristics perform. It has a command-line interface and a
browser-based GUI. Python 3 standard library only, nothing to install.

```
1 2 3        Goal state: tiles in order, blank in the bottom-right corner.
4 5 6        Slide tiles into the blank until the board matches the goal.
7 8 _
```

## The project in plain words

**The problem.** The 8-puzzle is a 3x3 board with eight numbered tiles and one empty
space. You can only slide a tile into the empty space. The goal is to get the tiles in
order (1 to 8) using as few slides as possible. A board can need up to 31 slides, and
there are about 181,000 reachable arrangements, so trying things blindly gets slow.

**What we built.** A program that solves any solvable 8-puzzle, shows the solution step by
step, and measures which solving strategy is best. It has a terminal version and a browser
version with an animated board.

**How the solver "thinks".** Think of every board arrangement as a spot on a map, and every
slide as a road to a neighbouring spot. Solving the puzzle means finding a route from the
starting board to the goal board. The solver explores this map, always keeping a to-do list
of boards it hasn't tried yet. The strategies differ in *which board they try next*:

1. **BFS (breadth-first search)** tries everything one slide away, then everything two
   slides away, and so on. It always finds the shortest solution, but it wastes time on
   boards that are clearly heading the wrong way.
2. **A\*** picks the board that looks most promising. "Promising" means
   *moves already made* + *a guess of moves still needed*. It also finds the shortest
   solution, but explores far fewer boards than BFS.
3. **Greedy best-first** looks only at the guess of moves still needed and rushes toward
   the goal. It is very fast, but the route it finds is often much longer than necessary.

**The "guess" is called a heuristic.** We try three, from weakest to smartest:

- **Misplaced tiles:** how many tiles are not in their right spot.
- **Manhattan distance:** how many squares each tile is away from its home, added up.
- **Manhattan + linear conflict:** the same, plus a penalty when two tiles are in their
  correct row or column but in each other's way.

None of them ever guesses *more* moves than are really needed. That is the property that
keeps A\* honest and guarantees the shortest solution. A smarter guess lets A\* skip more
useless boards.

**Making puzzles without typing.** The GUI and terminal can create a puzzle for you. They
start from the solved board and make a set number of random slides (6 for Easy, 14 for
Medium, 26 for Hard). Because the board is made by legal slides, it can always be solved.
"Hardest" uses a known board that needs the maximum 31 slides.

**What we found.** On 30 random puzzles, all of BFS and A\* found the same shortest
solutions, but BFS looked at about 92,000 boards on average, A\* with Manhattan about 2,400,
and A\* with linear conflict about 1,300. Greedy looked at only about 290 boards but gave
solutions nearly twice as long. In short: *a good guess makes the search dramatically
cheaper without losing the best answer.*

**How the pieces fit together.**

```
eight_puzzle.py   -> the solving brain (strategies, guesses, puzzle maker, terminal tool)
gui.py            -> a tiny local server that lets the web page ask the brain to solve
web/index.html    -> the page you see: board, buttons, animation, comparison table
```

When you press **Solve** in the browser, the page sends the current board to `gui.py`,
which runs the solver and sends back the list of moves. The page then replays those moves
on screen one by one.

## Files

| File | Purpose |
|---|---|
| `eight_puzzle.py` | Solver core and CLI: algorithms, heuristics, puzzle generation, benchmark |
| `gui.py` | Small local web server exposing the solver to the GUI |
| `web/index.html` | The GUI page (board, animation, comparison table) |

## Quick start

### GUI

```bash
python gui.py            # opens http://127.0.0.1:8000/ in your browser
python gui.py --port 9000 --no-browser
```

In the GUI you can:

- **Generate a puzzle** with one click, with no typing: *Easy*, *Medium*, *Hard*,
  *Hardest (31 moves)* or *Random*.
- **Play manually** by clicking a tile next to the gap.
- **Solve** with A\*, Greedy Best-First or BFS, and pick the heuristic. The solution is
  animated, with Play/Pause/Replay, Step and a speed slider.
- **See stats** for the last search: solution length, nodes expanded, search time.
- **Compare all** algorithms on the current board in one table.

### Command line

```bash
# Solve a specific board (9 numbers read row by row, 0 = blank).
# The solution is animated board by board in the terminal.
python eight_puzzle.py solve "1 2 3 4 0 6 7 5 8"

# Auto-generate a board instead of typing numbers
python eight_puzzle.py solve --level hard          # easy | medium | hard | hardest
python eight_puzzle.py solve --random              # fully random solvable board

# Choose algorithm and heuristic
python eight_puzzle.py solve --level hard -a astar -H linear_conflict
python eight_puzzle.py solve --level hard -a greedy -H manhattan
python eight_puzzle.py solve --level hard -a bfs

# Benchmark every algorithm on N random puzzles
python eight_puzzle.py compare -n 50 --seed 1
```

Useful flags for `solve`: `--seed N` repeats the same generated board, `--delay 0.2` changes
the animation speed (`0` prints all boards instantly), and `--quiet` skips the animation and
prints only the move list.

## How it works

**State:** a 9-tuple read row by row, with `0` as the blank. A move slides the blank
up, down, left or right.

**Solvability:** only half of all arrangements can reach the goal. A board is solvable
exactly when its number of *inversions* (pairs of tiles in the wrong order, ignoring the
blank) has the same parity as the goal's. Unsolvable boards are rejected.

**Difficulty levels:** a level scrambles the goal with a random walk of N legal moves
(Easy 6, Medium 14, Hard 26), never undoing the previous move. Since every step is a legal
move, the board is always solvable. *Hardest* picks one of the known 31-move boards, the
maximum possible depth for the 8-puzzle.

### Algorithms

| Algorithm | Evaluation `f(n)` | Optimal? |
|---|---|---|
| BFS | none (explores by depth) | Yes |
| A\* | `g(n) + h(n)` | Yes, if `h` is admissible |
| Greedy Best-First | `h(n)` | No |

`g(n)` is the number of moves made so far; `h(n)` is the heuristic estimate of moves left.

### Heuristics

All three are **admissible** (they never overestimate the true remaining moves), so A\*
with any of them returns a shortest solution.

1. **Misplaced tiles:** count of tiles not in their goal position.
2. **Manhattan distance:** sum over tiles of `|row - goal_row| + |col - goal_col|`.
   Each move shifts one tile by one square, so this is a lower bound.
3. **Manhattan + linear conflict:** adds 2 for every pair of tiles that sit in their goal
   row (or column) but in reversed order. One of them must leave the line and return,
   costing at least 2 extra moves. This dominates plain Manhattan.

Because `misplaced ≤ Manhattan ≤ Manhattan + linear conflict ≤ true cost`, the stronger
heuristics expand fewer nodes.

## Sample results

`python eight_puzzle.py compare -n 30 --seed 1` (30 random solvable puzzles):

| Algorithm | Avg nodes expanded | Avg solution length | Optimal |
|---|---|---|---|
| BFS | 92,637 | 23.23 | 30/30 |
| A\* + misplaced tiles | 20,362 | 23.23 | 30/30 |
| A\* + Manhattan | 2,376 | 23.23 | 30/30 |
| A\* + Manhattan + linear conflict | 1,322 | 23.23 | 30/30 |
| Greedy + Manhattan | 292 | 44.57 | 1/30 |

Takeaways:

- A\* with an admissible heuristic always matches BFS's (optimal) solution length while
  expanding far fewer nodes.
- A tighter heuristic means fewer expansions. Manhattan expands about 8x fewer nodes than
  misplaced tiles; linear conflict cuts Manhattan by roughly another 45%.
- Linear conflict is not always faster in wall-clock time, because each evaluation costs
  more.
- Greedy is the fastest and expands the fewest nodes, but its solutions are about twice as
  long as optimal.

Timings depend on your machine; node counts do not.

## Implementation notes

- A\* and Greedy share one priority-queue routine; a `best_g` table skips stale queue
  entries and re-opens a state if a cheaper path to it is found.
- A counter breaks ties between equal `f` values so the heap never compares states.
- The GUI is a plain HTML/JS page that talks to `gui.py` over a small JSON API
  (`/api/new`, `/api/solve`, `/api/compare`); the server only listens on `127.0.0.1`.

## Ideas for extension

- 15-puzzle with IDA\* (A\* runs out of memory there)
- Pattern-database heuristics
- Weighted A\* to trade optimality for speed
