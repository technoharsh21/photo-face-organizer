export interface FAQItem {
  id: string;
  category: 'General' | 'Privacy & Safety' | 'Features' | 'Installation & Hardware';
  question: string;
  answer: string;
}

export const FAQ_DATA: FAQItem[] = [
  {
    id: "cloud-privacy",
    category: "Privacy & Safety",
    question: "Does Photo Face Organizer upload my photos to any server?",
    answer: "No, never. Photo Face Organizer is 100% local-first software. All face detection, face recognition encoding, profile storage, and photo routing happen entirely on your computer's local CPU/GPU. No internet connection is required for photo scanning."
  },
  {
    id: "original-files",
    category: "Privacy & Safety",
    question: "What happens to my original photos during a scan?",
    answer: "Your original photos are never moved, deleted, renamed, or modified. Photo Face Organizer operates strictly in copy mode: it reads your source photos and creates clean copies inside your designated target output directory."
  },
  {
    id: "solo-scanning",
    category: "Features",
    question: "How does Solo Photo Scanning work?",
    answer: "Solo Photo Scanning enforces pure individual portraits. A photo is only copied into a person's folder if they are the ONLY person in the photo. The engine utilizes sensitive 360° SCRFD detection (90° side profile faces) and performs an automatic secondary deep exclusion verification pass to catch background bystanders or turned heads."
  },
  {
    id: "couple-solo",
    category: "Features",
    question: "Can I create Solo albums for exclusive 2-person couples?",
    answer: "Yes! If you select an exclusive 2-person group profile in Solo Mode (e.g. 'Me & Partner'), the scanner strictly requires that EXACTLY the 2 partners appear in the photo. If a 3rd person or stranger is present, the photo is excluded from the couple album."
  },
  {
    id: "duplicate-scanner",
    category: "Features",
    question: "How does the Duplicate Photo Finder detect duplicates?",
    answer: "The Duplicate Finder uses a 3-tier CPU cryptographic pipeline: (1) 0 ms file-size metadata filter, (2) hardware-accelerated SHA-256 hashing at multi-GB/s speed, and (3) smart auto-selection rules (keep oldest/newest/shortest path). Duplicates can be safely moved to your OS Recycle Bin or quarantine folder."
  },
  {
    id: "find-photos",
    category: "Features",
    question: "Can I search for photos of one person without running an organizing scan?",
    answer: "Yes. 'Find Photos by Person' is a read-only search: pick a person, add one or more folders, choose 'All Photos (Solo + Group Photos)' or 'Solo Photos Only', and matches stream onto the screen in real time with a per-photo similarity score. No output folder is created and nothing is written to disk unless you explicitly save the results. You can pause to inspect matches found so far, or stop early and keep them."
  },
  {
    id: "live-enrollment",
    category: "Features",
    question: "Do I need to find reference photos, or can I enroll someone from a webcam?",
    answer: "Both work. The 360° Live Face Scanner opens your webcam and guides the person through 5 angles (Look Straight, Turn Left, Turn Right, Tilt Up, Smile) to capture the multi-angle 512-d embeddings that make matching robust. Its hands-free 'Auto Scan' mode fires each shot itself once the head has held one pose stable for 12 consecutive frames and the frame passes the same 4-star quality gate used for reference photos, then completes enrollment on its own."
  },
  {
    id: "photo-viewer",
    category: "Features",
    question: "Can I review matched photos inside the app?",
    answer: "Yes. Any matched photo opens in a built-in lightbox showing the filename, its match percentage, and its position in the result set. Browse with the arrow keys, zoom with +/- or the scroll wheel, fit with F, show actual size with 1, rotate with R/L, and press Esc to close. It also reports each file's full path, pixel size, and modification date, and offers 'Open Location' and 'Save Photo' — both read-only against your library."
  },
  {
    id: "resume-scan",
    category: "Features",
    question: "What happens if a long scan is interrupted, crashes, or I cancel it?",
    answer: "Scan progress is checkpointed continuously. On the next launch the app detects the unfinished run and offers 'Resume Scan', 'Restart', or 'Discard Recovery'. Resuming re-reads the source folders and skips every file already recorded as processed, so a 40,000-photo job continues rather than starting over. Interrupted runs can also be resumed later from the Scan History table, which lists each run's date, status, file counts, matched and no-match totals, and duration."
  },
  {
    id: "face-cache",
    category: "Features",
    question: "Why is rescanning the same folders so much faster?",
    answer: "The optional Face Processing Disk Cache stores each photo's detected face locations and 512-d embeddings in a local SQLite database keyed by the file's SHA-256 content hash. Repeat scans read those numbers from disk instead of re-running the neural network (about 0.0005 s per photo). Because the key is a content hash, a modified or replaced photo is automatically re-processed. 'Clear Cache' reports how many entries and megabytes it frees and never touches your photos."
  },
  {
    id: "move-mode",
    category: "Privacy & Safety",
    question: "Is there a Move mode that actually relocates photos?",
    answer: "Yes, and it is gated. Move Mode first copies every photo to the output directory exactly as Copy Mode does, then re-reads each copy to verify it is present and readable on disk. Only if the whole run verifies does the app ask whether to delete the originals — and that dialog defaults to 'No'. If any copy fails verification, it warns you and deletes nothing. Photos are never removed silently."
  },
  {
    id: "scan-boundary",
    category: "Privacy & Safety",
    question: "Can a scan wander outside the folders I selected?",
    answer: "No. Photo discovery is boundary-isolated: only the folders you add (plus their subfolders when recursive is on) are walked, symbolic links are not followed, and every resolved path is checked to confirm it still lies inside the selected folder before it is queued. A stray symlink pointing at another drive or your home directory cannot pull a scan outside the boundary you chose."
  },
  {
    id: "diagnostic-logs",
    category: "Installation & Hardware",
    question: "How do I check which accelerator is in use, or report a performance problem?",
    answer: "The Settings page shows the live binding (for example 'Active AI Hardware: NVIDIA CUDA GPU (GPU Accelerated)') and the loaded model, and 'View Diagnostic Logs' opens the local photo_face_organizer.log — which records provider selection and any inference fallback — with buttons to copy it to the clipboard or open the file. The sidebar footer also carries a persistent 'GPU:' or 'CPU:' badge. All logs stay on your disk."
  },
  {
    id: "quality-ratings",
    category: "Features",
    question: "What are the 4 and 5-star quality rating requirements?",
    answer: "Every face is scored on resolution, focus sharpness (Laplacian variance), and lighting. To maintain high scanning precision, only faces scoring 4 or 5 stars (clear, sharp, well-lit) are accepted into Person Profiles or saved in Unknown Faces. Blurry or low-res crops are automatically rejected."
  },
  {
    id: "clean-outliers",
    category: "Features",
    question: "What does the 'Clean Outliers' button do?",
    answer: "On any profile, clicking '🧹 Clean Outliers' automatically computes the core centroid facial vector and purges reference photos that do not match the person's identity (< 60% similarity), as well as any low-quality photos (< 4 stars)."
  },
  {
    id: "group-photos",
    category: "Features",
    question: "Does it support standard group photos with multiple people?",
    answer: "Yes! In standard scan mode, if a photo contains multiple recognized faces (e.g. Alice AND Bob), the application copies that photo into Alice's folder, Bob's folder, and any Group Profile folder that requires both Alice and Bob together."
  },
  {
    id: "format-support",
    category: "Features",
    question: "Which photo file formats are supported?",
    answer: "Photo Face Organizer supports JPEG/JPG, PNG, WebP, BMP, TIFF/TIF, Apple HEIC/HEIF, and professional camera RAW formats — Canon CR2, Nikon NEF, Sony ARW, Adobe DNG, Olympus ORF, Panasonic RW2, Pentax PEF, and Fujifilm RAF — with automatic EXIF orientation correction."
  },
  {
    id: "gpu-support",
    category: "Installation & Hardware",
    question: "Which GPUs and hardware accelerators are supported?",
    answer: "Photo Face Organizer features a Universal Hardware Engine that auto-detects and binds to: (1) DirectX 12 DirectML on Windows (supports NVIDIA, AMD Radeon, and Intel Arc / Iris Xe GPUs), (2) NVIDIA CUDA & TensorRT, (3) AMD ROCm on Linux, (4) Apple Silicon Neural Engine CoreML (M1/M2/M3/M4 on macOS), (5) Intel OpenVINO, and (6) High-throughput Multi-Core CPU fallback."
  },
  {
    id: "supported-os",
    category: "Installation & Hardware",
    question: "Which operating systems are supported?",
    answer: "Photo Face Organizer supports 64-bit Linux (Ubuntu, Debian, Mint, Fedora, Arch), Windows (10/11 64-bit), and macOS (Apple Silicon M-series & Intel)."
  },
  {
    id: "multiple-folders",
    category: "General",
    question: "Can I scan multiple folders or entire hard drives at once?",
    answer: "Yes, you can select multiple source folders and enable recursive scanning to analyze all subdirectories automatically in a single scan run."
  },
  {
    id: "app-data-location",
    category: "General",
    question: "Where is my profile and scan history data stored?",
    answer: "All profiles, face encodings, and scan history are saved in standard OS application data locations (e.g., ~/.local/share/PhotoFaceOrganizer on Linux, %APPDATA%/PhotoFaceOrganizer on Windows). No data ever leaves your computer."
  }
];
