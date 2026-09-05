# Photo Face Organizer — Future Feature Roadmap 🚀

This roadmap outlines proposed future functionalities, architectural designs, and implementation plans for **Photo Face Organizer**. Each feature is designed to maintain the application's core principles: **100% data safety (never alter originals), high performance, intuitive dark-themed UI, and offline local privacy**.

---

## 📋 Table of Contents
1. [Milestone 1: Smart Metadata & Storage-Saving Organization](#milestone-1-smart-metadata--storage-saving-organization)
2. [Milestone 2: Automation & Background Sync](#milestone-2-automation--background-sync)
3. [Milestone 3: Semantic Natural Language Search (CLIP AI)](#milestone-3-semantic-natural-language-search-clip-ai)
4. [Milestone 4: Interactive Review, Lightbox & Quality Curation](#milestone-4-interactive-review-lightbox--quality-curation)
5. [Milestone 5: Video Face Recognition & Export Hub](#milestone-5-video-face-recognition--export-hub)
6. [Milestone 6: Scalability & Database Indexing](#milestone-6-scalability--database-indexing)
7. [Feature Matrix & Priority Tracking](#feature-matrix--priority-tracking)

---

## Milestone 1: Smart Metadata & Storage-Saving Organization

### 1.1 EXIF Date & Event-Based Subfolder Organization
* **Goal**: Organize photos inside person/group folders chronologically or by event.
* **Folder Pattern Options**:
  * `Output/{Person}/{YYYY}/{YYYY-MM-DD}/photo.jpg`
  * `Output/{Person}/{YYYY}/{Month_Name}/photo.jpg`
  * `Output/{Person}/Flat/photo.jpg` (Current default)
* **Technical Design**:
  * Extract DateTimeOriginal from EXIF using `Pillow.ExifTags` with fallback to file creation timestamp (`mtime`).
  * Add configurable folder template parser in `services/output_service.py`.
  * Add dropdown in **New Scan Wizard** & **Settings** to select organization template.

### 1.2 Direct EXIF / IPTC / XMP Face Tagging
* **Goal**: Write detected names directly to photo metadata tags without moving or duplicating files.
* **Value**: Photos become instantly searchable by person name in **Windows Explorer, macOS Spotlight, Apple Photos, Adobe Lightroom, and Google Photos**.
* **Technical Design**:
  * Integrate lightweight metadata writer (`piexif` or `py3exiv2`).
  * Tag standard IPTC Keywords (`IPTC:Keywords`) and XMP Subject (`XMP:Subject`, `XMP-mwg-rs:Regions`).
  * Add toggle: *"Tag Metadata in In-Place Mode (No Copy)"* in New Scan page.

### 1.3 Zero-Disk-Space Hardlinks & Symlinks
* **Goal**: Organize photos without duplicating file size on disk.
* **Supported Modes**:
  1. **Copy** (`shutil.copy2`): Full isolated copies (current safe default).
  2. **Hardlink** (`os.link`): 0 bytes extra disk space, instant creation, works on same drive/filesystem.
  3. **Symlink / Shortcut** (`os.symlink`): Pointer to original file.
* **Safety Guards**: Verify destination filesystem matches source before hardlinking, with automatic fallback to copy if cross-device.

---

## Milestone 2: Automation & Background Sync

### 2.1 "Watch Folder" Continuous Auto-Organizer
* **Goal**: Background daemon that automatically scans and organizes new photos as they are added (e.g., camera SD card imports, Downloads, Dropbox/Nextcloud sync folders).
* **Technical Design**:
  * Utilize `watchfiles` (already in `requirements.txt`) in a background `QThread` daemon.
  * Debounce file events (wait 2s after write completion before scanning).
  * System tray notifications when new photos are detected and organized.
  * UI: New "Watch Folders" tab in Settings to manage active monitored paths.

### 2.2 Profile Merging, Splitting & Alias Support
* **Goal**: Manage person profiles flexibly.
* **Features**:
  * **Merge**: Combine two profiles (e.g. "Harsh (Young)" and "Harsh") into one unified profile with all reference embeddings intact.
  * **Split**: Move selected face crops from one profile to create another.
  * **Aliases / Nicknames**: Support multiple search names for a profile (e.g. "Dad", "John Doe").

---

## Milestone 3: Semantic Natural Language Search (CLIP AI)

### 3.1 Local Natural Language Search (Text-to-Photo)
* **Goal**: Search photos by text descriptions: *"beach sunset"*, *"wedding cake"*, *"dog playing with ball"*, *"receipt"*, *"person holding guitar"*.
* **Architecture**:
  * Run local ONNX export of **MobileCLIP** or **OpenCLIP ViT-B/32** via existing `onnxruntime` engine.
  * Index 512-dim visual embeddings during initial scan alongside ArcFace face embeddings.
  * Search UI: Global search bar on Dashboard and Results page supporting combined queries (e.g., *"Person: Harsh"* + *"Text: at the beach"*).
* **Performance**: Fast vector similarity search with cosine distance against indexed embeddings.

### 3.2 Bystander Privacy Blur / Face Redaction
* **Goal**: Anonymize photos before sharing publicly.
* **Features**:
  * One-click blur/pixelate all **Unknown Faces** or background bystanders while keeping recognized profile faces sharp.
  * Adjustable blur intensity (Gaussian Blur / Pixelation / Blackout Box).

---

## Milestone 4: Interactive Review, Lightbox & Quality Curation

### 4.1 Interactive Face Review & Correction Grid
* **Goal**: Fast keyboard-driven UI to verify edge-case matches and unknown face suggestions.
* **Key Controls**:
  * `Y` / `Enter` → Confirm Match
  * `N` / `Delete` → Reject Match (Send to Unknown)
  * `R` / `Tab` → Reassign to another Person
* **UI Layout**: Rapid masonry thumbnail grid showing cropped face with match confidence percentage badges.

### 4.2 Built-in High-Performance Lightbox & Photo Viewer
* **Goal**: Inspect photos without opening external apps.
* **Features**:
  * Full-screen preview with smooth zoom, pan, and rotation.
  * Bounding box overlay toggle showing face boxes, pose classification, and confidence scores on hover.
  * EXIF metadata inspector sidebar (Camera model, focal length, ISO, exposure, GPS map coordinates).

### 4.3 Best-Shot / Hero Photo Selector & Blink Detection
* **Goal**: Help users find the best photo in a burst/sequence.
* **Metrics**:
  * **Sharpness Score**: Laplacian variance calculation to flag blurry photos.
  * **Blink Detection**: Eye aspect ratio (EAR) from SCRFD facial landmarks to detect closed eyes.
  * **Smile Score**: Facial landmark ratio to highlight best expressions.

---

## Milestone 5: Video Face Recognition & Export Hub

### 5.1 Video Scanning & Timeline Bookmarking
* **Goal**: Find people inside video clips (`.mp4`, `.mov`, `.mkv`, `.avi`).
* **Technical Design**:
  * Extract keyframes at configurable sample rates (e.g., 1 frame per second) using OpenCV `cv2.VideoCapture`.
  * Group detections into timestamp ranges (e.g., *"Harsh appears at 00:45 - 01:20 and 04:10 - 05:00"*).
  * Generate HTML/JSON video chapter bookmarks or lossless video cuts via FFmpeg.

### 5.2 Export Hub & Contact Sheets
* **Goal**: Share organized photos in clean formats.
* **Export Options**:
  * **Printable PDF Album / Contact Sheet**: Grid of photos with custom title and date stamps.
  * **Standalone Web Gallery**: Self-contained single-file HTML/JS photo gallery for sharing with family.
  * **ZIP Archive Package**: One-click zipped person folder.

---

## Milestone 6: Scalability & Database Indexing

### 6.1 Persistent SQLite / Vector Database Index
* **Goal**: Instant scanning of 100,000+ photo libraries.
* **Technical Design**:
  * Replace JSON/JSONL flat files with a local SQLite database (`library.db`) with WAL mode.
  * Store file metadata: `path`, `mtime`, `sha256`, `face_bboxes`, `embeddings`, `clip_embeddings`.
  * Re-scans skip unmodified files in sub-milliseconds by checking `(path, mtime, size)`.

---

## Feature Matrix & Priority Tracking

| Feature | Category | Priority | Target Status |
| :--- | :--- | :---: | :---: |
| **EXIF Date & Timeline Folders** | Smart Organization | 🔴 High | Planned |
| **Hardlinks & Symlinks Mode** | Smart Organization | 🔴 High | Planned |
| **Direct EXIF / IPTC Face Tagging** | Metadata | 🔴 High | Planned |
| **Watch Folder Auto-Sync** | Automation | 🟡 Medium | Planned |
| **Face Review & Verification Grid** | UI / UX | 🟡 Medium | Planned |
| **Built-in Lightbox & Viewer** | UI / UX | 🟡 Medium | Planned |
| **SQLite Library Indexing** | Performance | 🟡 Medium | Planned |
| **Natural Language Search (CLIP)** | AI Superpower | 🟢 Future | Planned |
| **Best-Shot & Blink Detection** | AI Superpower | 🟢 Future | Planned |
| **Video Face Recognition** | Media Expansion | 🟢 Future | Planned |
| **Export Hub (PDF / Web Gallery)** | Sharing | 🟢 Future | Planned |
| **Privacy Anonymizer / Face Blur** | Privacy | 🟢 Future | Planned |

---

> *Note: For contributing or implementing any feature above, create a dedicated task branch and unit tests under `tests/`.*
