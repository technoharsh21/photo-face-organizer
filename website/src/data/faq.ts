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
    answer: "Photo Face Organizer supports JPEG, JPG, PNG, WebP, TIFF, BMP, Apple HEIC/HEIF photos, and professional camera RAW formats (Canon CR2/CR3, Nikon NEF, Sony ARW, DNG, Fujifilm RAF, Olympus ORF) with automatic EXIF orientation correction."
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
