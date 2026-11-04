"""Browser GUI for the 8-puzzle solver (standard library only).

    python gui.py [--port 8000] [--no-browser]

Serves web/index.html and a tiny JSON API backed by eight_puzzle.py.
"""
import argparse
import json
import random
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import eight_puzzle as ep

INDEX = Path(__file__).parent / "web" / "index.html"
CONFIGS = [("bfs", None), ("astar", "misplaced"), ("astar", "manhattan"),
           ("astar", "linear_conflict"), ("greedy", "manhattan")]


def solve_one(state, algo, heur):
    t = time.perf_counter()
    moves, expanded = ep.run(algo, heur, state)
    return {"moves": moves, "length": len(moves), "expanded": expanded,
            "ms": round((time.perf_counter() - t) * 1000, 1)}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, INDEX.read_bytes(), "text/html; charset=utf-8")
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        try:
            req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if self.path == "/api/new":
                level = req.get("level", "random")
                if level not in ("random", "hardest", *ep.LEVELS):
                    raise ValueError("unknown level")
                self._send(200, {"state": list(ep.level_state(level, random.Random()))})
                return
            if self.path in ("/api/solve", "/api/compare"):
                state = tuple(req["state"])
                if sorted(state) != list(range(9)) or not ep.is_solvable(state):
                    raise ValueError("invalid or unsolvable board")
                if self.path == "/api/solve":
                    algo, heur = req.get("algo", "astar"), req.get("heuristic", "manhattan")
                    if algo not in ("astar", "greedy", "bfs") or heur not in ep.HEURISTICS:
                        raise ValueError("unknown algorithm or heuristic")
                    self._send(200, solve_one(state, algo, heur))
                else:
                    rows = [{"algo": a, "heuristic": h, **solve_one(state, a, h)} for a, h in CONFIGS]
                    for r in rows:
                        del r["moves"]
                    self._send(200, {"rows": rows})
                return
            self._send(404, {"error": "not found"})
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
            self._send(400, {"error": str(e)})

    def log_message(self, *args):
        pass


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--no-browser", action="store_true")
    args = p.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"8-puzzle GUI running at {url}  (Ctrl+C to stop)")
    if not args.no_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
