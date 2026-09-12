# Photo Face Organizer 📸🤖

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![UI Framework](https://img.shields.io/badge/GUI-PySide6%20(Qt6)-41CD52.svg?logo=qt&logoColor=white)](https://www.qt.io/)
[![Vision Engine](https://img.shields.io/badge/AI%20Engine-InsightFace%20%7C%20ArcFace%20512D-FF6F00.svg)](https://github.com/deepinsight/insightface)
[![Hardware Acceleration](https://img.shields.io/badge/Acceleration-CUDA%20%7C%20DirectML%20%7C%20CoreML%20%7C%20CPU-76B900.svg)](https://onnxruntime.ai/)
[![Test Suite](https://img.shields.io/badge/Tests-63%20Passed-brightgreen.svg)]()

An advanced, high-performance, **100% offline and privacy-first** desktop application that automatically detects, recognizes, clusters, and organizes messy photo collections into person and group directories using state-of-the-art Deep Face Recognition.

---

## 📑 Table of Contents

- [🌟 Key Superpowers & Features](#-key-superpowers--features)
- [🧠 Architecture & AI Engine](#-architecture--ai-engine)
- [📸 Core Workflows & Walkthrough](#-core-workflows--walkthrough)
  - [1. Profile Enrollment & Hands-Free Live 3D Pose Scanner](#1-profile-enrollment--hands-free-live-3d-pose-scanner)
  - [2. Interactive "Find Photos by Person"](#2-interactive-find-photos-by-person)
  - [3. Batch Scan & Organization Wizard](#3-batch-scan--organization-wizard)
  - [4. Solo Scan (0% False-Positive Mode)](#4-solo-scan-0-false-positive-mode)
  - [5. Unknown Faces Clustering](#5-unknown-faces-clustering)
  - [6. Exact & Perceptual Duplicate Finder](#6-exact--perceptual-duplicate-finder)
  - [7. Zero Data Loss & Audit Reconciliation](#7-zero-data-loss--audit-reconciliation)
- [💻 System Requirements](#-system-requirements)
- [📦 Installation Guide](#-installation-guide)
  - [Option 1: Run from Source (Recommended)](#option-1-run-from-source-recommended)
  - [Option 2: Install via Pip from GitHub](#option-2-install-via-pip-from-github)
  - [Option 3: Pre-built Binary / Installer](#option-3-pre-built-binary--installer)
- [⚡ Hardware Acceleration & GPU Setup](#-hardware-acceleration--gpu-setup)
- [📁 Supported File Formats](#-supported-file-formats)
- [⚙️ Settings & Configuration](#️-settings--configuration)
- [🛠️ Developer Guide & Testing](#️-developer-guide--testing)
  - [Running Tests](#running-tests)
  - [Live Auto-Reload Dev Mode](#live-auto-reload-dev-mode)
  - [Building Standalone Installers](#building-standalone-installers)
- [🔒 Privacy & Offline Guarantee](#-privacy--offline-guarantee)
- [🚀 Future Roadmap](#-future-roadmap)
- [📄 License](#-license)

---

## 🌟 Key Superpowers & Features

| Feature | Description |
| :--- | :--- |
| **🧠 Dual-Engine AI Vision** | Powered by **InsightFace SCRFD 360°** face detector and **ArcFace 512-D neural embeddings** achieving 99.86% LFW benchmark accuracy. |
| **🎥 Hands-Free Live 3D Pose Scanner** | Interactive live webcam enrollment with an intelligent 5-pose keypoint classifier (**Frontal, Turn Left, Turn Right, Look Up, Smile**) and real-time star quality gating (≥4★). |
| **🔍 Interactive Photo Discovery** | Search for anyone across multiple directories in real-time. Filter by **Solo Photos** (person is alone) or **All Photos** (solo + group) with an integrated high-performance Lightbox viewer. |
| **👥 Compulsory Group Profiles** | Create group profiles (e.g., *"Mom & Dad"*, *"Family Vacation"*) that require **all compulsory members** to be present in the photo together. |
| **🎯 Solo Scan (0% False Positives)** | Calibrated multi-stage verification engine designed specifically for isolating individual people without false-positive spillover. |
| **❓ Unknown Faces Clustering** | Unsupervised face clustering groups unrecognized faces together so you can create new profiles with a single click. |
| **🔍 Exact Duplicate Finder** | SHA-256 and size-filtered duplicate scanner with smart selection rules (*Keep Oldest*, *Keep Newest*, *Keep Shortest Path*) and safe actions (OS Trash, Quarantine, Permanent Delete). |
| **🛡️ 100% Data Safety & Audit** | **Never alters original files**. Built-in file audit reconciliation verifies that 100% of discovered photos are accounted for with zero data loss. |
| **⚡ Hardware Acceleration** | Auto-detects and leverages **NVIDIA CUDA**, **Microsoft DirectML** (all DirectX 12 GPUs including Intel Arc & AMD Radeon), **Apple CoreML**, and multi-threaded CPU fallback. |
| **📷 Universal Format Support** | Native support for JPEG, PNG, WebP, BMP, TIFF, Apple **HEIC/HEIF**, and Camera RAW formats (**CR2, NEF, ARW, DNG, RAF, RW2, PEF**). |
| **📜 Crash Recovery & History** | Crash-resilient logging, native C++ segfault handler (`faulthandler`), and automatic resume prompt for interrupted scans. |

---

## 🧠 Architecture & AI Engine

Photo Face Organizer is built with clean architecture principles separating domain logic, asynchronous background services, and reactive Qt UI components:

```
photo-face-organizer/
├── app.py                      # Application bootstrap, crash handler & Qt main loop
├── config.py                   # Platform data paths, configurations & directory layout
├── dev.py                      # Nodemon-like auto-reloading watcher for rapid dev
├── domain/                     # Pure business logic & AI inference engines
│   ├── insight_engine.py       # SCRFD + ArcFace ONNX Runtime inference & provider management
│   ├── face_engine.py          # Abstract engine interface & dlib/fallback bindings
│   ├── pose_classifier.py      # 5-keypoint geometric 3D head pose classification
│   ├── auto_capture_controller.py # State machine for automated camera capture
│   ├── calibration.py          # Similarity calibration & threshold calculation
│   ├── duplicate_detector.py   # In-memory SHA-256 hash index for destination deduplication
│   ├── image_loader.py         # Multi-format decoder (Pillow, pillow-heif, rawpy, tifffile)
│   ├── matcher.py              # Person & compulsory group matching logic
│   ├── solo_matcher.py         # Calibrated single-person matching
│   └── scanner.py              # Recursive directory discovery & file iterator
├── services/                   # Background QThread workers & persistence layers
│   ├── scan_service.py         # Batch scanning & organization pipeline
│   ├── solo_scan_service.py    # Dedicated solo scanning worker
│   ├── find_photos_service.py  # Real-time interactive photo search worker
│   ├── profile_service.py      # Profile management, multi-crop embeddings & quality assessment
│   ├── unknown_face_service.py # Face clustering & unknown cluster management
│   ├── duplicate_service.py    # Directory duplicate scanning, grouping & quarantine
│   ├── face_cache_service.py   # Embedding cache indexed by (path, mtime, size)
│   ├── history_service.py      # JSONL scan logs, stats & undo tracking
│   └── settings_service.py     # Atomically persisted user preferences
├── ui/                         # PySide6 modern dark-themed interface
│   ├── main_window.py          # Main layout, categorized sidebar navigation & crash prompt
│   ├── styles.py               # Custom dark QSS stylesheet & palette
│   ├── pages/                  # Modular view controllers
│   │   ├── dashboard_page.py   # System stats, active profiles, hardware status & quick actions
│   │   ├── people_page.py      # Profile manager (add, edit, webcam enroll, calibrate)
│   │   ├── find_photos_page.py # Real-time photo explorer with Lightbox viewer
│   │   ├── new_scan_page.py    # Scan wizard (sources, destination, copy/move, rules)
│   │   ├── solo_scan_page.py   # High-precision individual scan setup
│   │   ├── processing_page.py  # Live progress bars, ETA, logs & live thumbnail feed
│   │   ├── results_page.py     # Scan summaries, output tree & reconciliation report
│   │   ├── unknown_faces_page.py # Unknown face cluster gallery & 1-click enrollment
│   │   ├── duplicate_page.py   # Duplicate photo sets, side-by-side comparison & cleanup
│   │   ├── history_page.py     # Historic scan records & folder reopen
│   │   └── settings_page.py    # Hardware device selector, thresholds & cache management
│   └── components/             # Reusable UI widgets & modal dialogs
│       ├── live_face_scanner_dialog.py # Webcam 3D live auto-capture & calibration modal
│       ├── photo_viewer_dialog.py      # Lightbox viewer with zoom & pan
│       ├── face_selector.py            # Crop selection & profile thumbnail manager
│       ├── crash_recovery_dialog.py    # Resume prompt for unexpected exits
│       └── skipped_files_dialog.py     # Non-image or unreadable files report
└── tests/                      # Full pytest unit & integration test suite
```

---

## 📸 Core Workflows & Walkthrough

### 1. Profile Enrollment & Hands-Free Live 3D Pose Scanner
- **Sample Photos**: Upload 1 to 10+ reference photos per person. The system computes multiple 512-dimensional vector embeddings to capture lighting, age, and hairstyle variations.
- **Hands-Free Live Webcam Scanner**:
  - Open the webcam enrollment tool.
  - Choose between **Auto Scan** and **Manual Capture**.
  - In **Auto Scan**, simply turn your head naturally. The real-time pose classifier automatically captures 5 distinct angles:
    1. **Frontal** (neutral face)
    2. **Turn Left** (yaw > 0.35)
    3. **Turn Right** (yaw < -0.35)
    4. **Tilt Up** (pitch < 0.30)
    5. **Smile** (mouth spread > 1.05)
  - Built-in sharpness, resolution, and illumination checks ensure only high-quality samples (≥4 stars) are saved.

### 2. Interactive "Find Photos by Person"
- Select any person from your profiles.
- Choose directories or drives to search.
- Select your mode:
  - **Solo Photos**: Returns only photos where this specific person is alone in the frame.
  - **All Photos**: Returns both solo photos and group pictures containing the person.
- Matches stream onto your screen in real time with progressive rendering.
- Double-click any image to open the built-in **Lightbox Viewer** with smooth zoom, pan, and direct file export.

### 3. Batch Scan & Organization Wizard
- Add multiple source folders containing tens of thousands of mixed photos.
- Configure target destination and mode:
  - **Copy Mode** (Safe default, preserves originals).
  - **Move Mode** (Moves files directly into organized structures).
- Select active person profiles and **Compulsory Group Folders**.
- Group folders require **all** specified people to be detected together in the photo.
- Configure conflict resolution (Skip, Auto-rename, or Overwrite).

### 4. Solo Scan (0% False-Positive Mode)
- Specially tuned for strict individual photo extraction (e.g. creating personal portfolios or model books).
- Employs calibrated cosine margin thresholds and multi-face exclusion filters to guarantee 0% false positives.

### 5. Unknown Faces Clustering
- Faces detected in photos that do not match any existing profile are extracted and clustered using unsupervised feature clustering.
- Browse clusters in the **Unknown Faces** tab.
- Convert any cluster into a brand-new profile with a single click or merge into an existing profile.

### 6. Exact & Perceptual Duplicate Finder
- Fast 2-stage duplicate detection:
  1. Instant byte-size grouping.
  2. SHA-256 block hashing on matching file sizes.
- View side-by-side comparisons with path and resolution metadata.
- Apply batch selection rules (*Keep Oldest*, *Keep Newest*, *Keep Shortest Path*).
- Safely resolve duplicates by sending them to **System Trash**, moving them to a **Quarantine Folder**, or deleting them permanently.

### 7. Zero Data Loss & Audit Reconciliation
- Original photos are never modified, edited, or destroyed.
- At the end of every scan, the **Audit Reconciliation Engine** validates that:
  $$\text{Discovered Photos} = \text{Organized Files} + \text{Unmatched Files} + \text{Skipped Files}$$
- An itemized reconciliation report displays the exact count and disk location of every file.

---

## 💻 System Requirements

- **Operating System**:
  - **Linux**: Ubuntu 20.04+, Debian 11+, Fedora 36+, Arch Linux
  - **Windows**: Windows 10 / Windows 11 (64-bit)
  - **macOS**: macOS 12 (Monterey) or newer (Intel & Apple Silicon M1/M2/M3/M4)
- **Python**: Python `3.10`, `3.11`, or `3.12`
- **Memory (RAM)**: Minimum 4 GB RAM (8 GB+ recommended for large libraries)
- **Disk Space**: ~500 MB for application and AI models

---

## 📦 Installation Guide

### Option 1: Run from Source (Recommended)

#### 1. Clone the repository
```bash
git clone https://github.com/technoharsh21/photo-face-organizer.git
cd photo-face-organizer
```

#### 2. Create and activate a virtual environment
- **On Linux / macOS:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```
- **On Windows (Command Prompt / PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\activate
  ```

#### 3. Install system dependencies (Linux only)
```bash
# Ubuntu / Debian
sudo apt-get update
sudo apt-get install -y cmake build-essential libgl1 libglx-mesa0 libglib2.0-0
```

#### 4. Install Python dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 5. Launch the application
```bash
python app.py
```

---

### Option 2: Install via Pip from GitHub
```bash
pip install git+https://github.com/technoharsh21/photo-face-organizer.git
photo-face-organizer
```

---

### Option 3: Pre-built Binary / Installer

- **Windows**: Download `PhotoFaceOrganizer_Setup.exe` from the GitHub Releases page and follow the standard installation wizard.
- **Linux**: Download the `.deb` package or standalone directory archive.

---

## ⚡ Hardware Acceleration & GPU Setup

The application automatically checks for available hardware acceleration at startup:

```
[Hardware Acceleration Auto-Detection Hierarchy]
  ├── 1. NVIDIA CUDA GPU (onnxruntime-gpu) ──> Fastest (NVIDIA GeForce/RTX/Quadro)
  ├── 2. Microsoft DirectML (onnxruntime-directml) ──> High Performance (AMD, Intel, NVIDIA on Windows)
  ├── 3. Apple CoreML (onnxruntime) ──> Hardware Neural Engine on Apple Silicon
  └── 4. Multi-Core CPU Fallback ──> Optimized multi-threaded execution on all platforms
```

### Enabling NVIDIA CUDA (Linux / Windows)
If you have an NVIDIA GPU with CUDA installed:
```bash
pip uninstall onnxruntime onnxruntime-directml -y
pip install onnxruntime-gpu
```

### Enabling DirectML (Windows - AMD, Intel Arc, NVIDIA)
```bash
pip uninstall onnxruntime onnxruntime-gpu -y
pip install onnxruntime-directml
```

You can change your preferred compute device at any time under **Settings ➔ Device Preference** (`Auto`, `GPU`, `CPU`).

---

## 📁 Supported File Formats

Photo Face Organizer uses a robust multi-decoder pipeline (`Pillow`, `pillow-heif`, `rawpy`, `tifffile`) that extracts image data and orientation tags safely without altering disk files:

| Format Category | Supported Extensions | Engine / Decoder |
| :--- | :--- | :--- |
| **Standard Images** | `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp` | Pillow + OpenCV |
| **Apple HEIC / HEIF** | `.heic`, `.heif` | `pillow-heif` (High-efficiency iOS photos) |
| **High Dynamic / TIFF** | `.tif`, `.tiff` | `tifffile` / Pillow |
| **Canon RAW** | `.cr2`, `.cr3` (preview extraction) | `rawpy` |
| **Nikon RAW** | `.nef` | `rawpy` |
| **Sony RAW** | `.arw` | `rawpy` |
| **Adobe Digital Negative** | `.dng` | `rawpy` |
| **Fujifilm RAW** | `.raf` | `rawpy` |
| **Olympus / Panasonic / Pentax** | `.orf`, `.rw2`, `.pef` | `rawpy` |

---

## ⚙️ Settings & Configuration

Application data and configuration files are stored safely in standard platform directories:

- **Linux**: `~/.local/share/PhotoFaceOrganizer/`
- **Windows**: `%LOCALAPPDATA%\PhotoFaceOrganizer\`
- **macOS**: `~/Library/Application Support/PhotoFaceOrganizer/`

### Directory Layout
```
PhotoFaceOrganizer/
├── profiles/               # Saved person profiles, crops & vector embeddings
├── duplicates/             # SHA-256 destination hash indices
├── quarantine/             # Safely isolated duplicate photos
├── history/                # Scans ledger (scans.jsonl)
├── settings/               # Persisted user settings (settings.json)
├── cache/                  # Fast face embedding cache
└── photo_face_organizer.log # Auto-flushing diagnostic logs
```

### Key Configurable Settings
- **Device Preference**: `Auto`, `GPU`, or `CPU`.
- **Performance Mode**:
  - `Eco` (Low CPU/battery usage)
  - `Balanced` (Default, smooth responsive UI)
  - `Maximum Performance` (Full multi-core batch processing)
- **Matching Threshold**: Adjust similarity threshold (Default: `50.0%` - `55.0%`).
- **Face Cache**: Enable/clear in-memory face embedding cache to accelerate repeated scans.

---

## 🛠️ Developer Guide & Testing

### Running Tests
The project includes a comprehensive test suite covering pose classification, image loaders, matchers, caching, services, and UI flows.

```bash
# Run all unit and integration tests
pytest

# Run tests with verbose output
pytest -v

# Run a specific test module
pytest tests/test_pose_classifier.py
pytest tests/test_auto_capture_controller.py
pytest tests/test_find_photos.py
```

### Live Auto-Reload Dev Mode
For rapid UI and service development, launch the app with `dev.py`. It watches all Python files and automatically restarts the application when changes are saved:

```bash
python dev.py
```

### Building Standalone Installers

#### Windows (PyInstaller + Inno Setup)
```powershell
# 1. Package Python application into dist/PhotoFaceOrganizer/
pyinstaller --noconfirm --onedir --windowed --name "PhotoFaceOrganizer" --icon="icon.ico" --exclude-module tkinter --exclude-module matplotlib --hidden-import scipy.spatial --collect-all insightface --collect-all onnxruntime --collect-all pillow_heif app.py

# 2. Compile Inno Setup Installer
ISCC.exe setup.iss
```

#### Linux (.deb / Tarball)
```bash
# Run PyInstaller
pyinstaller --noconfirm --onedir --windowed --name "PhotoFaceOrganizer" --icon="icon.png" --collect-all insightface --collect-all onnxruntime --collect-all pillow_heif app.py
```

---

## 🔒 Privacy & Offline Guarantee

- 🛡️ **100% Offline**: All face detection, vector embedding, matching, and clustering algorithms run **locally on your machine**.
- 🚫 **Zero Telemetry**: No photos, face crops, or telemetry data are ever transmitted over the network.
- 🔏 **Non-Destructive**: Original source files are treated as strictly read-only during analysis.

---

## 🚀 Future Roadmap

For technical specifications, milestone plans, and upcoming features (e.g., EXIF date hierarchy, semantic CLIP text search, bystander blur, video face recognition), check out the [Future Feature Roadmap](ROADMAP.md).

---

## 📄 License

This project is open-source and licensed under the [MIT License](LICENSE).

---

## 👥 Authors & Acknowledgments

- **Lead Developer**: [Harsh](https://github.com/technoharsh21) (<support@technoharsh.com>)
- Powered by [InsightFace](https://github.com/deepinsight/insightface), [PySide6 / Qt](https://www.qt.io/), [ONNX Runtime](https://onnxruntime.ai/), and [Pillow](https://python-pillow.org/).


