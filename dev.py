"""
Dev Launcher - Nodemon-like Auto-Reloader for Photo Face Organizer.

Watches all python code files in the codebase. Whenever any file is saved or modified,
it automatically terminates the running app process and restarts it cleanly!
"""

import os
import subprocess
import sys
from pathlib import Path
from watchfiles import watch

# Disable bytecode caching
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True


def start_app_process():
    print("🔄 [AUTO-RELOAD] Starting Photo Face Organizer (app.py)...")
    return subprocess.Popen([sys.executable, "app.py"])


def main():
    root_dir = Path(__file__).parent.resolve()
    print(f"👀 [AUTO-RELOAD] Watching for file changes in {root_dir} (Nodemon-style)...")
    proc = start_app_process()

    try:
        for changes in watch(root_dir):
            py_changes = [path for change_type, path in changes if path.endswith(".py")]
            if py_changes:
                changed_names = [Path(p).name for p in py_changes]
                print(f"\n⚡ [AUTO-RELOAD] Detected changes in: {', '.join(changed_names)}. Restarting app...")

                if proc and proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()

                proc = start_app_process()
    except KeyboardInterrupt:
        print("\n🛑 [AUTO-RELOAD] Stopping watcher and terminating application.")
        if proc and proc.poll() is None:
            proc.terminate()


if __name__ == "__main__":
    main()
