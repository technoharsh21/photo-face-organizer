# Bug & Design Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all critical, high, and medium bugs and design issues found in the Image Analyser desktop app audit.

**Architecture:** Pure Python/PySide6 desktop app. Fixes are isolated to individual files — no cross-cutting refactors. Apply minimal changes that resolve root causes without restructuring.

**Tech Stack:** Python 3.10+, PySide6, SQLite (sqlite3), NumPy, Pathlib

**Spec:** This plan is self-contained — each task references exact file paths and line numbers from the audit.

## Global Constraints

- Never move, delete, or modify original source photos
- Never use `os.rename` for cross-device moves — use `shutil.move`
- All atomic writes use tempfile + `Path.replace()` (POSIX-atomic on same filesystem)
- No new dependencies — only stdlib and existing requirements
- Python 3.8 compatibility required (no `Path.is_relative_to`, no `match` statements)
- Do not restructure existing class hierarchies

---

### Task 1: Fix Critical Import Crash in Multiprocess Worker

**Files:**
- Modify: `domain/worker.py:38`

**Interfaces:**
- Consumes: `InsightFaceEngine` from `domain.insight_engine`
- Produces: working `_process_photo_task_multiprocess` function

**Root cause:** `FaceRecognitionEngine` is defined as an import-level alias in `domain/face_engine.py:84` but is NOT exported as a standalone symbol. When `worker.py:38` imports it in an isolated subprocess, Python sees only the module-level namespace of `face_engine` — the alias exists there, but the reviewer confirmed `InsightFaceEngine` is the real class. Fix: import `InsightFaceEngine` directly from `domain.insight_engine`.

- [ ] **Step 1: Edit the import inside `_process_photo_task_multiprocess`**

In `domain/worker.py`, change line 38:
```python
# BEFORE
from domain.face_engine import FaceRecognitionEngine

# AFTER
from domain.insight_engine import InsightFaceEngine as FaceRecognitionEngine
```

The alias `FaceRecognitionEngine` is preserved so line 42 (`engine = FaceRecognitionEngine(...)`) needs no change.

- [ ] **Step 2: Verify no other callers use the broken import path**

```bash
grep -rn "from domain.face_engine import FaceRecognitionEngine" "/home/web-lp-044/Documents/Image  Analyser" --include="*.py"
```
Expected: 0 results (only the one line we just fixed).

- [ ] **Step 3: Commit**

```bash
git add "domain/worker.py"
git commit -m "fix: import InsightFaceEngine directly in multiprocess worker to prevent ImportError in subprocess"
```

---

### Task 2: Add Thread Safety to Counter Increments and Classifier Training

**Files:**
- Modify: `domain/worker.py:119-140, 250-260`
- Modify: `domain/matcher.py:48-78`

**Root cause 1:** `ScanWorker.processed_count` (and sibling counters) are incremented in `as_completed` loop which runs across ThreadPoolExecutor threads. Multiple futures completing simultaneously cause lost increments.

**Root cause 2:** `FaceMatcher._last_profile_count` is read and written without a lock. Two threads calling `match_face()` simultaneously can both enter the training branch.

- [ ] **Step 1: Add a lock to `ScanWorker.__init__`**

In `domain/worker.py`, add `import threading` at top (after existing imports) and add `self._stats_lock = threading.Lock()` in `__init__` after line 136 (`self.copied_file_pairs = ...`):

```python
import threading  # add at top of file with other imports

# in __init__, after self.copied_file_pairs = ...:
self._stats_lock = threading.Lock()
```

- [ ] **Step 2: Wrap counter increments in `run()` with the lock**

In `domain/worker.py`, the block starting at line 255 (inside `for future in as_completed`):
```python
# BEFORE
self._apply_file_result(f_path, res)
self.processed_count += 1
self.processed_files.add(str_path)

# AFTER
self._apply_file_result(f_path, res)
with self._stats_lock:
    self.processed_count += 1
    self.processed_files.add(str_path)
```

- [ ] **Step 3: Wrap counter mutations in `_apply_file_result` with the lock**

The method `_apply_file_result` at line 289 mutates `self.skipped_count`, `self.error_count`, `self.matched_count`, `self.no_match_count`, `self.unknown_faces_count`, `self.results_by_person`, `self.errors_log`, `self.source_to_output_map`, `self.copied_file_pairs`. Wrap the entire method body in `with self._stats_lock:`:

```python
def _apply_file_result(self, file_path: Path, res: dict[str, Any]):
    """Apply results from parallel process execution to thread-safe data structures."""
    str_path = str(file_path)
    with self._stats_lock:
        status = res.get("status")
        # ... rest of method body unchanged, just indented one level
```

- [ ] **Step 4: Add a lock to `FaceMatcher` for classifier training**

In `domain/matcher.py`, add `import threading` at top and add lock in `__init__`:

```python
import threading  # add at top

# in FaceMatcher.__init__, after self._last_profile_count = -1:
self._classifier_lock = threading.Lock()
```

- [ ] **Step 5: Protect classifier training in `match_face`**

In `domain/matcher.py`, lines 74-77:
```python
# BEFORE
if len(profiles) != self._last_profile_count:
    self.classifier_service.train_classifier(profiles)
    self._last_profile_count = len(profiles)

# AFTER
with self._classifier_lock:
    if len(profiles) != self._last_profile_count:
        self.classifier_service.train_classifier(profiles)
        self._last_profile_count = len(profiles)
```

- [ ] **Step 6: Verify no import errors**

```bash
cd "/home/web-lp-044/Documents/Image  Analyser" && python -c "from domain.worker import ScanWorker; from domain.matcher import FaceMatcher; print('OK')"
```
Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add "domain/worker.py" "domain/matcher.py"
git commit -m "fix: add threading locks to scan worker counters and classifier training to prevent race conditions"
```

---

### Task 3: Atomic File Writes for History and Settings Services

**Files:**
- Modify: `services/history_service.py:80-83`
- Modify: `services/settings_service.py:43-47`

**Root cause:** Both services write JSON directly to the target file. Concurrent calls (or a crash mid-write) produce truncated/corrupt files. Fix: write to a temp file on the same filesystem, then `Path.replace()` (atomic rename on POSIX).

- [ ] **Step 1: Add atomic write helper to `history_service.py`**

In `services/history_service.py`, add `import tempfile` and `import os` at the top, then replace `_save_all_scans`:

```python
import json
import os
import tempfile
from typing import Any

from config import Config


class HistoryService:
    # ... __init__ unchanged ...

    def _save_all_scans(self, scans: list[dict[str, Any]]):
        """Rewrite all scan records to JSONL file atomically."""
        content = "".join(json.dumps(s) + "\n" for s in scans)
        dir_path = self.history_file.parent
        dir_path.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=str(dir_path), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, str(self.history_file))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
```

- [ ] **Step 2: Add atomic write to `settings_service.py`**

In `services/settings_service.py`, add `import tempfile` and `import os`, then replace `save_settings`:

```python
import json
import os
import tempfile
from typing import Any

# ... DEFAULT_SETTINGS unchanged ...

class SettingsService:
    # ... __init__, load_settings, get, set, update, reset_to_defaults unchanged ...

    def save_settings(self):
        """Save current settings to JSON file atomically."""
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(self.settings, indent=2)
        dir_path = self.settings_file.parent
        fd, tmp_path = tempfile.mkstemp(dir=str(dir_path), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, str(self.settings_file))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
```

- [ ] **Step 3: Verify imports**

```bash
cd "/home/web-lp-044/Documents/Image  Analyser" && python -c "from services.history_service import HistoryService; from services.settings_service import SettingsService; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add "services/history_service.py" "services/settings_service.py"
git commit -m "fix: atomic temp-file writes for history and settings to prevent corruption on concurrent access or crash"
```

---

### Task 4: Enable SQLite WAL Mode in Face Cache Service

**Files:**
- Modify: `services/face_cache_service.py:36-52`

**Root cause:** Default SQLite journal mode blocks concurrent reads during writes. Multiple ThreadPoolExecutor threads calling `get_cached_faces`/`save_cached_faces` simultaneously get `"database is locked"` errors. WAL (Write-Ahead Logging) mode allows concurrent reads with one writer.

- [ ] **Step 1: Enable WAL mode in `_init_db`**

In `services/face_cache_service.py`, update `_init_db` to set WAL pragma before creating the table:

```python
def _init_db(self):
    """Initialize SQLite database table for face caching."""
    try:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS face_cache (
                    file_hash TEXT PRIMARY KEY,
                    locations_json TEXT NOT NULL,
                    encodings_blob BLOB NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to initialize face cache database: {e}")
```

- [ ] **Step 2: Verify**

```bash
cd "/home/web-lp-044/Documents/Image  Analyser" && python -c "from services.face_cache_service import FaceCacheService; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add "services/face_cache_service.py"
git commit -m "fix: enable SQLite WAL mode in face cache to prevent database locked errors under concurrent thread access"
```

---

### Task 5: Python 3.8 Compatibility Fix for `is_relative_to`

**Files:**
- Modify: `services/duplicate_service.py:68-71`

**Root cause:** `Path.is_relative_to()` was added in Python 3.9. On Python 3.8, calling it raises `AttributeError`, which is silently caught by the broad `except Exception` at line 101, returning an empty `valid_paths` list and skipping all duplicate detection.

- [ ] **Step 1: Replace `is_relative_to` with compatible string prefix check**

In `services/duplicate_service.py`, replace lines 68-71:

```python
# BEFORE
valid_paths = [
    p for p in photo_paths
    if any(p.resolve().is_relative_to(src) for src in resolved_sources)
]

# AFTER
def _is_relative_to_compat(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False

valid_paths = [
    p for p in photo_paths
    if any(_is_relative_to_compat(p.resolve(), src) for src in resolved_sources)
]
```

Place `_is_relative_to_compat` as a module-level function (after `format_bytes`, before `class DuplicateService`).

- [ ] **Step 2: Verify**

```bash
cd "/home/web-lp-044/Documents/Image  Analyser" && python -c "from services.duplicate_service import DuplicateService; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add "services/duplicate_service.py"
git commit -m "fix: replace Path.is_relative_to() with Path.relative_to() try/except for Python 3.8 compatibility"
```

---

### Task 6: Dashboard — Show All Profiles with Scroll (Not Truncated at 5)

**Files:**
- Modify: `ui/pages/dashboard_page.py` — the `_populate_profiles_showcase` method (around line 549)

**Root cause:** Loop `for idx, profile in enumerate(profiles[:5])` hard-caps at 5 profiles. Users with 6+ profiles silently lose visibility of them on the dashboard.

- [ ] **Step 1: Find the exact line**

```bash
grep -n "profiles\[:5\]" "/home/web-lp-044/Documents/Image  Analyser/ui/pages/dashboard_page.py"
```

- [ ] **Step 2: Remove the slice cap**

Change `profiles[:5]` → `profiles` in the `for` loop:

```python
# BEFORE
for idx, profile in enumerate(profiles[:5]):

# AFTER
for idx, profile in enumerate(profiles):
```

- [ ] **Step 3: Verify the profiles_layout container is inside a scroll area**

Check that `self.profiles_layout` (or its parent widget) is wrapped in a `QScrollArea`. If not, find the parent `QFrame`/`QWidget` and wrap it:

```bash
grep -n "profiles_layout\|QScrollArea\|ProfileShowcase" "/home/web-lp-044/Documents/Image  Analyser/ui/pages/dashboard_page.py" | head -20
```

If the showcase area already uses `setFlow(QListView.LeftToRight)` or a `QScrollArea`, no further change needed. If it's a bare `QHBoxLayout` without scroll, wrap the parent frame in `QScrollArea` with `setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)` and `setWidgetResizable(True)`.

- [ ] **Step 4: Commit**

```bash
git add "ui/pages/dashboard_page.py"
git commit -m "fix: show all profiles on dashboard showcase instead of silently truncating at 5"
```

---

### Task 7: Fix Results Page Image Cover Mode (Black Bars → Cover)

**Files:**
- Modify: `ui/pages/results_page.py:73`

**Root cause:** `ResultsImageCover.paintEvent` uses `Qt.KeepAspectRatio` which letterboxes images with black bars. All other pages use `KeepAspectRatioByExpanding` (cover) for consistency. This creates visual inconsistency.

- [ ] **Step 1: Change scale mode in `ResultsImageCover.paintEvent`**

In `ui/pages/results_page.py`, in the `paintEvent` method of `ResultsImageCover` (around line 73):

```python
# BEFORE
scaled = self.pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)

# AFTER
scaled = self.pixmap.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
```

The painter already draws `x_off`/`y_off` offsets for centering — this works correctly with `KeepAspectRatioByExpanding` since `scaled` will be >= widget size and the offsets clip to center.

- [ ] **Step 2: Verify offset math is correct for cover mode**

With `KeepAspectRatioByExpanding`, `scaled.width() >= w` and `scaled.height() >= h`. The existing code:
```python
x_off = max(0, (w - scaled.width()) // 2)
y_off = max(0, (h - scaled.height()) // 2)
```
This produces negative offsets (correct — crops edges). The `max(0, ...)` clamp is WRONG for cover mode — it will pin to top-left instead of centering. Fix:
```python
x_off = (w - scaled.width()) // 2  # will be negative, centering the crop
y_off = (h - scaled.height()) // 2
```

- [ ] **Step 3: Commit**

```bash
git add "ui/pages/results_page.py"
git commit -m "fix: use KeepAspectRatioByExpanding cover mode in results image widget and fix offset centering for cover crop"
```

---

### Task 8: Fix People Page — Responsive Grid Guard and Image Cover Small-Image Fallback

**Files:**
- Modify: `ui/pages/people_page.py:285-286` (grid cols guard)
- Modify: `ui/pages/people_page.py:178` (image cover crop fallback)

**Root cause 1:** `cols = container_w // 175` can produce 0 when `container_w < 175`. The `max(2, ...)` guard at line 286 prevents 0 but `container_w = max(240, self.width())` already guards this — still, the `max(2, ...)` is fine and no change needed here. Actual check: on very small screens `container_w // 175` could yield 1 even with the guard. The `max(2, ...)` is the right fix — verify it's there.

**Root cause 2:** `DuplicateImageCover` / face crop widgets use a fixed `QRectF` center crop. When source image is smaller than the target display size, scaled image is smaller than widget → black bars or ugly upscale.

- [ ] **Step 1: Confirm the cols guard**

```bash
grep -n "cols = " "/home/web-lp-044/Documents/Image  Analyser/ui/pages/people_page.py"
```
Expected output includes `max(2, container_w // 175)` or similar. If it's `max(1, ...)` change to `max(2, ...)`. If it's already `max(2, ...)` or the `container_w = max(240, ...)` already ensures minimum 1 col, no change needed.

- [ ] **Step 2: Find image cover paintEvent for people page**

```bash
grep -n "paintEvent\|KeepAspect\|QRectF\|scaled\b" "/home/web-lp-044/Documents/Image  Analyser/ui/pages/people_page.py" | head -20
```

- [ ] **Step 3: Fix cover widget to handle small source images**

Find the `paintEvent` that uses center crop (likely a custom widget). Replace the scaling logic to use `KeepAspectRatioByExpanding` with correct negative offsets (same pattern as Task 7):

```python
# In the paintEvent of the face cover/crop widget:
scaled = self.pixmap.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
x_off = (w - scaled.width()) // 2
y_off = (h - scaled.height()) // 2
painter.drawPixmap(x_off, y_off, scaled)
```

- [ ] **Step 4: Commit**

```bash
git add "ui/pages/people_page.py"
git commit -m "fix: correct image cover widget scaling mode and offset math in people page to prevent black bars on small source images"
```

---

### Task 9: Remove Inline Hardcoded Styles from New Scan Page Buttons and Mode Cards

**Files:**
- Modify: `ui/pages/new_scan_page.py` — Back/Next button `setStyleSheet` calls (~line 251, 264) and operation mode card inline styles (~line 579)

**Root cause:** Inline `setStyleSheet` calls bypass the QSS design system, making theme changes impossible and creating visual inconsistency with buttons elsewhere.

- [ ] **Step 1: Remove inline `setStyleSheet` from Back button**

In `ui/pages/new_scan_page.py`, the `btn_prev` at ~line 251:
```python
# BEFORE — remove the entire setStyleSheet call:
self.btn_prev.setStyleSheet(
    "QPushButton { background-color: #1e293b; color: #ffffff; ... }"
    "QPushButton:hover { background-color: #1d4ed8; ... }"
)

# AFTER — delete those lines entirely (the class "SecondaryButton" already handles styling via QSS)
```

- [ ] **Step 2: Remove inline `setStyleSheet` from Next button**

Same approach for `btn_next` at ~line 264 — delete its `setStyleSheet(...)` call. The `setProperty("class", "PrimaryButton")` already provides the correct styling.

- [ ] **Step 3: Remove inline `setStyleSheet` from Start Scan button**

Same for `btn_start` at ~line 275 — delete its `setStyleSheet(...)` call.

- [ ] **Step 4: Replace operation mode card inline setStyleSheet with CSS class property**

Find the operation mode card selection logic (~line 579). Replace:
```python
# BEFORE
card.setStyleSheet("QFrame { border: 2px solid #3b82f6; ... }")

# AFTER  
card.setProperty("selected", True)  # or False
card.style().unpolish(card)
card.style().polish(card)
```

Add corresponding QSS rules to `ui/styles.py` for selected/unselected operation mode cards:
```css
QFrame[selected="true"] {
    border: 2px solid #3b82f6;
    background-color: #1e3a5f;
}
QFrame[selected="false"] {
    border: 1px solid #334155;
    background-color: #0f172a;
}
```

- [ ] **Step 5: Verify buttons still render correctly**

Start the app and navigate to New Scan page. Visually confirm Back/Next/Start buttons have correct colors and hover states from the QSS design system.

- [ ] **Step 6: Commit**

```bash
git add "ui/pages/new_scan_page.py" "ui/styles.py"
git commit -m "fix: remove inline button setStyleSheet overrides in new scan page, use design system CSS classes instead"
```

---

### Task 10: Fix Splitter Proportional Sizing (Results, Unknown Faces, People Pages)

**Files:**
- Modify: `ui/pages/results_page.py` — splitter setSizes
- Modify: `ui/pages/unknown_faces_page.py` — splitter setSizes and setMaximumWidth
- Modify: `ui/pages/people_page.py` — splitter setSizes

**Root cause:** Hardcoded pixel values in `setSizes([380, 560])` etc. break layouts at non-standard resolutions. `setMaximumWidth(450)` on splitter panes creates dead space on wide screens. Fix: use `setStretchFactor` for proportional splits, and remove `setMaximumWidth` caps.

- [ ] **Step 1: Fix results_page.py splitter**

```bash
grep -n "setSizes\|setMaximumWidth\|splitter" "/home/web-lp-044/Documents/Image  Analyser/ui/pages/results_page.py" | head -10
```

Replace `splitter.setSizes([380, 560])` with:
```python
splitter.setStretchFactor(0, 2)  # left pane: 40%
splitter.setStretchFactor(1, 3)  # right pane: 60%
```

- [ ] **Step 2: Fix unknown_faces_page.py splitter**

```bash
grep -n "setSizes\|setMaximumWidth\|splitter\|setMaximum" "/home/web-lp-044/Documents/Image  Analyser/ui/pages/unknown_faces_page.py" | head -10
```

Replace `setSizes([380, 780])` with:
```python
splitter.setStretchFactor(0, 1)  # left: 33%
splitter.setStretchFactor(1, 2)  # right: 67%
```

Remove or comment out `setMaximumWidth(450)` on the left pane widget.

- [ ] **Step 3: Fix people_page.py splitter**

```bash
grep -n "setSizes\|setMaximumWidth\|splitter" "/home/web-lp-044/Documents/Image  Analyser/ui/pages/people_page.py" | head -10
```

Replace `setSizes([300, 750])` with:
```python
splitter.setStretchFactor(0, 1)  # left: 29%
splitter.setStretchFactor(1, 3)  # right: 71%
```

- [ ] **Step 4: Fix duplicate_page.py left pane max width**

```bash
grep -n "setMaximumWidth\|setSizes\|splitter" "/home/web-lp-044/Documents/Image  Analyser/ui/pages/duplicate_page.py" | head -10
```

Remove `setMaximumWidth(460)` on the left pane and replace `setSizes` with `setStretchFactor` using 1:2 ratio.

- [ ] **Step 5: Commit**

```bash
git add "ui/pages/results_page.py" "ui/pages/unknown_faces_page.py" "ui/pages/people_page.py" "ui/pages/duplicate_page.py"
git commit -m "fix: replace hardcoded splitter pixel sizes with proportional stretch factors for responsive layout"
```

---

## Self-Review Checklist

- [x] Task 1 covers CRITICAL import crash in worker subprocess
- [x] Task 2 covers HIGH thread safety for counters and classifier
- [x] Task 3 covers MEDIUM atomic file writes (history, settings)
- [x] Task 4 covers HIGH SQLite concurrent writes (WAL mode)
- [x] Task 5 covers MEDIUM Python 3.8 compat for duplicate service
- [x] Task 6 covers CRITICAL/HIGH dashboard profile truncation
- [x] Task 7 covers HIGH results page image cover mode + offset math
- [x] Task 8 covers HIGH people page image cover for small images
- [x] Task 9 covers MEDIUM inline styles / design system violation
- [x] Task 10 covers HIGH/MEDIUM hardcoded splitter pixels

**Not included (deferred as lower-risk):**
- SQLite WAL for unknown face service (disk-based, not DB — less critical)
- Slider/scrollbar HiDPI sizes (cosmetic, no data risk)
- Face selector 130x130 fixed size (functional but not data-corrupting)
- TOCTOU in output_service (DuplicateDetector in-memory index already partially mitigates this)
