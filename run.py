#!/usr/bin/env python3
"""
run.py — One-command launcher for the full app (backend + frontend).

Starts BOTH:
  1. Flask backend        -> http://localhost:5000   (backend/app.py)
  2. Vite React dev server -> http://localhost:5173   (frontend/, proxies API to :5000)

Usage:
    python run.py              # dev mode: Flask on :5000 + Vite dev server on :5173
    python run.py --build      # build the React app first, then serve dist/ from Flask only
                               # (single URL: http://localhost:5000)

Dependencies are installed AUTOMATICALLY when missing — you never need to run
the install commands yourself:
    pip install -r backend/requirements.txt     (auto-run if flask/cv2 missing)
    cd frontend && npm install                  (auto-run if node_modules missing)

Ctrl+C stops both processes cleanly.
"""

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT, "backend")
FRONTEND_DIR = os.path.join(ROOT, "frontend")


def find_npm():
    """Locate the npm executable (npm.cmd on Windows, npm elsewhere)."""
    if os.name == "nt":
        return "npm.cmd"
    npm = shutil.which("npm")
    if npm is None:
        print("[run.py] ERROR: 'npm' not found on PATH.")
        print("          Install Node.js (>=18) from https://nodejs.org and try again.")
        sys.exit(1)
    return npm


class Launcher:
    def __init__(self):
        self.processes = []
        self.stopping = False

    def start(self, cmd, cwd, env=None, name=""):
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=merged_env,
            # Own process group on POSIX so we can kill children (vite/esbuild) too.
            preexec_fn=os.setsid if os.name != "nt" else None,
        )
        self.processes.append((name or " ".join(cmd), proc))
        return proc

    def stop_all(self):
        if self.stopping:
            return
        self.stopping = True
        print("\n[run.py] Stopping all services...")
        for name, proc in self.processes:
            if proc.poll() is None:
                try:
                    if os.name == "nt":
                        proc.terminate()
                    else:
                        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    pass
        # Graceful window, then force-kill anything left.
        deadline = time.time() + 5
        for _, proc in self.processes:
            while proc.poll() is None and time.time() < deadline:
                time.sleep(0.1)
            if proc.poll() is None:
                try:
                    if os.name == "nt":
                        proc.kill()
                    else:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
        print("[run.py] All services stopped.")

    def wait(self):
        """Block until any child exits; then shut everything down."""
        try:
            while True:
                for name, proc in self.processes:
                    code = proc.poll()
                    if code is not None:
                        print(f"\n[run.py] '{name}' exited with code {code}. Shutting down.")
                        return code
                time.sleep(0.5)
        except KeyboardInterrupt:
            return 0


def run_install(cmd, cwd, what):
    """Run a dependency-install command; abort with a clear message on failure."""
    print(f"[run.py] {what} ...")
    print(f"[run.py]   $ {' '.join(cmd)}  (cwd: {os.path.relpath(cwd, ROOT) or '.'})")
    try:
        result = subprocess.run(cmd, cwd=cwd)
    except KeyboardInterrupt:
        print("\n[run.py] Installation interrupted.")
        sys.exit(130)
    except FileNotFoundError:
        print(f"[run.py] ERROR: '{cmd[0]}' not found. Install Node.js/npm or Python pip first.")
        sys.exit(1)
    if result.returncode != 0:
        print(f"[run.py] ERROR: {what} FAILED (exit code {result.returncode}).")
        sys.exit(result.returncode)


def check_prerequisites():
    """Auto-install anything that is missing, then re-verify."""
    # ---- Python dependencies (flask, cv2, ...) ----
    try:
        import flask  # noqa: F401
        import cv2  # noqa: F401
    except ImportError:
        reqs = os.path.join(BACKEND_DIR, "requirements.txt")
        run_install(
            [sys.executable, "-m", "pip", "install", "-r", reqs],
            cwd=ROOT,
            what="Installing Python dependencies (pip install -r backend/requirements.txt)",
        )
        try:
            import flask  # noqa: F401
            import cv2  # noqa: F401
        except ImportError as exc:
            print(f"[run.py] ERROR: Python deps still missing after install ({exc.name}).")
            print("          Try manually:  python3 -m pip install -r backend/requirements.txt")
            sys.exit(1)

    # ---- Frontend dependencies (node_modules) ----
    if not os.path.isdir(os.path.join(FRONTEND_DIR, "node_modules")):
        run_install([find_npm(), "install"], cwd=FRONTEND_DIR,
                    what="Installing frontend dependencies (npm install)")
        if not os.path.isdir(os.path.join(FRONTEND_DIR, "node_modules")):
            print("[run.py] ERROR: frontend/node_modules still missing after npm install.")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Run backend (Flask) and frontend (Vite React) together.")
    parser.add_argument(
        "--build",
        action="store_true",
        help="Build the React app (npm run build) and serve it from Flask at http://localhost:5000 (no Vite dev server).",
    )
    args = parser.parse_args()

    check_prerequisites()
    launcher = Launcher()

    # Ensure Ctrl+C / kill stops every child process cleanly.
    # Using default SIGINT handling means Ctrl+C raises KeyboardInterrupt in
    # BOTH this process and any child sharing our terminal; the try/except in
    # `if __name__ == "__main__"` guarantees stop_all() runs on the way out.
    signal.signal(signal.SIGTERM, lambda *_: launcher.stop_all())

    if args.build:
        print("[run.py] Building React frontend (npm run build)...")
        try:
            result = subprocess.run([find_npm(), "run", "build"], cwd=FRONTEND_DIR)
        except KeyboardInterrupt:
            launcher.stop_all()
            sys.exit(0)
        if result.returncode != 0:
            print("[run.py] Frontend build failed.")
            sys.exit(result.returncode)
        # Flask already serves frontend/dist (SPA fallback) — just run the backend.
        print("[run.py] Starting Flask backend serving the built app at http://localhost:5000 ...")
        launcher.start([sys.executable, "app.py"], cwd=BACKEND_DIR, name="flask-backend")
    else:
        # 1) Backend
        print("[run.py] Starting Flask backend on http://localhost:5000 ...")
        launcher.start([sys.executable, "app.py"], cwd=BACKEND_DIR, name="flask-backend")

        # Give Flask a moment so Vite's proxy has a target when the page loads.
        time.sleep(2)

        # 2) Frontend dev server
        print("[run.py] Starting Vite React dev server on http://localhost:5173 ...")
        launcher.start([find_npm(), "run", "dev"], cwd=FRONTEND_DIR, name="vite-frontend")

        print(
            "\n============================================================\n"
            "  Open the app in your browser:\n"
            "    Frontend (React dev):  http://localhost:5173\n"
            "    Backend  (Flask/API):  http://localhost:5000\n"
            "  Press Ctrl+C to stop both.\n"
            "============================================================\n"
        )

    code = launcher.wait()
    launcher.stop_all()
    sys.exit(code)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Ctrl+C while waiting on children — ensure cleanup still happens.
        print("\n[run.py] Interrupted.")
        sys.exit(0)
