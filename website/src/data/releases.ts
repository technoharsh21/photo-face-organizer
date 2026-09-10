export interface Asset {
  name: string;
  filename: string;
  url: string;
  size: string;
  type: 'deb' | 'zip' | 'exe' | 'dmg' | 'pip';
  architecture?: string;
  sha256?: string;
  available: boolean;
  notes?: string;
}

export interface PlatformAssets {
  windows: Asset[];
  linux: Asset[];
  macos: Asset[];
}

export interface Release {
  version: string;
  releaseDate: string;
  isLatest: boolean;
  title: string;
  highlights: string[];
  notes: string[];
  assets: PlatformAssets;
  knownIssues?: string[];
}

export const RELEASES_DATA: Release[] = [
  {
    version: "v1.0.0",
    releaseDate: "2026-08-28",
    isLatest: true,
    title: "Official Initial Open-Source Release",
    highlights: [
      "InsightFace AI Engine: SCRFD 360° multi-angle face detection paired with ArcFace 512-dimensional recognition vectors",
      "Universal GPU Acceleration: TensorRT / CUDA (NVIDIA), DirectML (NVIDIA, AMD Radeon & Intel Arc on Windows), ROCm (AMD), OpenVINO (Intel), CoreML (Apple Silicon), with automatic multi-core CPU fallback",
      "Find Photos by Person: read-only live search across any folders, with Solo vs All matching, real-time match streaming, and a built-in lightbox",
      "Precision Solo Photo Scanning: 360° profile-angle detection with secondary deep background exclusion verification, plus exclusive couple & duo solo mode",
      "Compulsory Group Profiles: a group folder only receives a photo when every compulsory member is detected in it",
      "360° Live Face Enrollment: train a profile from a webcam across 5 head angles, including hands-free auto-capture gated on 4-star face quality",
      "4 & 5-Star Quality Gates: scoring across resolution, focus sharpness (Laplacian variance), and lighting, with 1-click 'Clean Outliers' identity purging",
      "Cryptographic Duplicate Photo Finder: instant file-size pre-filter plus SHA-256 validation, with keep-oldest / keep-newest / shortest-path rules and quarantine",
      "Unknown Faces Clustering: auto-group unmatched faces and promote a whole cluster into a new profile in one click",
      "Continuous Checkpointing & Crash Recovery: interrupted, cancelled, or crashed scans resume from where they stopped instead of restarting",
      "File Reconciliation Audit: every scan proves 100% of discovered photos are accounted for, with an exportable skipped-file audit log (.txt / .json)",
      "Face Processing Disk Cache: embeddings cached by SHA-256 content hash, making repeat scans of a known library near-instant",
      "Strict Scan Boundary Isolation: selected folders only, symbolic links never followed, and resolved paths verified to stay inside the chosen boundary",
      "Verified Move Mode: originals are offered for deletion only after every copy is re-read and confirmed on disk",
      "Universal Format Support: JPEG, PNG, WebP, BMP, TIFF, Apple HEIC/HEIF, and camera RAW (CR2, NEF, ARW, DNG, ORF, RW2, PEF, RAF) with EXIF orientation correction",
      "100% Local & Non-Destructive: no cloud upload, no account, and original photos are never moved, renamed, or modified in Copy mode"
    ],
    notes: [
      "First stable production-ready release of Photo Face Organizer, released under the MIT license.",
      "Supports 64-bit Linux (Debian/Ubuntu and derivatives), Windows 10/11 x64, and macOS on both Apple Silicon and Intel.",
      "All profiles, face encodings, caches, checkpoints, and logs are stored in the standard per-user application data directory and never leave the machine.",
      "Hardware acceleration is negotiated at startup with a graceful CPU fallback, so a missing or failing GPU provider never blocks a scan."
    ],
    assets: {
      linux: [
        {
          name: "Debian / Ubuntu Package (.deb)",
          filename: "photo-face-organizer_1.0.0_amd64.deb",
          url: "https://github.com/technoharsh21/photo-face-organizer/releases/download/v1.0.0/photo-face-organizer_1.0.0_amd64.deb",
          size: "188 MB",
          type: "deb",
          architecture: "amd64 (64-bit)",
          available: true,
          notes: "Official release package with ROCm / OpenVINO / CPU acceleration. Install via: sudo dpkg -i photo-face-organizer_1.0.0_amd64.deb"
        },
        {
          name: "Linux Standalone Bundle (.zip)",
          filename: "PhotoFaceOrganizer_Linux.zip",
          url: "https://github.com/technoharsh21/photo-face-organizer/releases/download/v1.0.0/PhotoFaceOrganizer_Linux.zip",
          size: "352 MB",
          type: "zip",
          architecture: "x86_64",
          available: true,
          notes: "No installation required — extract and run the PhotoFaceOrganizer executable inside."
        },
        {
          name: "Install from Source (pip / pipx)",
          filename: "photo-face-organizer (Git source)",
          url: "https://github.com/technoharsh21/photo-face-organizer",
          size: "Source",
          type: "pip",
          available: true,
          notes: "Install via: pip install git+https://github.com/technoharsh21/photo-face-organizer.git"
        }
      ],
      windows: [
        {
          name: "Windows Setup Installer (.exe)",
          filename: "PhotoFaceOrganizer_Setup.exe",
          url: "https://github.com/technoharsh21/photo-face-organizer/releases/download/v1.0.0/PhotoFaceOrganizer_Setup.exe",
          size: "135 MB",
          type: "exe",
          architecture: "x64 (DirectX 12 / DirectML & CUDA)",
          available: true,
          notes: "Inno Setup wizard with Desktop & Start Menu shortcuts and universal DirectML GPU acceleration on NVIDIA, AMD Radeon, and Intel Arc GPUs."
        }
      ],
      macos: [
        {
          name: "macOS Disk Image (.dmg)",
          filename: "PhotoFaceOrganizer_macOS.dmg",
          url: "https://github.com/technoharsh21/photo-face-organizer/releases/download/v1.0.0/PhotoFaceOrganizer_macOS.dmg",
          size: "164 MB",
          type: "dmg",
          architecture: "Apple Silicon (M1/M2/M3/M4) & Intel",
          available: true,
          notes: "Native macOS disk image with Apple Neural Engine CoreML acceleration."
        },
        {
          name: "macOS Standalone Bundle (.zip)",
          filename: "PhotoFaceOrganizer_macOS.zip",
          url: "https://github.com/technoharsh21/photo-face-organizer/releases/download/v1.0.0/PhotoFaceOrganizer_macOS.zip",
          size: "520 MB",
          type: "zip",
          architecture: "Apple Silicon (M1/M2/M3/M4) & Intel",
          available: true,
          notes: "Drag PhotoFaceOrganizer.app to your Applications folder. If Gatekeeper blocks the first launch, right-click → Open."
        }
      ]
    },
    knownIssues: []
  }
];

export function getReleases(): Release[] {
  return RELEASES_DATA;
}

export function getLatestRelease(): Release {
  return RELEASES_DATA.find((r) => r.isLatest) || RELEASES_DATA[0];
}

export function getReleaseByVersion(version: string): Release | undefined {
  const normalized = version.startsWith('v') ? version : `v${version}`;
  return RELEASES_DATA.find((r) => r.version.toLowerCase() === normalized.toLowerCase());
}

export type SupportedOS = 'windows' | 'linux' | 'macos' | 'unknown';

export function getPrimaryAssetForOS(release: Release, os: SupportedOS): Asset | null {
  if (os === "windows" && release.assets.windows.length > 0) {
    return release.assets.windows[0];
  }
  if (os === "linux" && release.assets.linux.length > 0) {
    return release.assets.linux[0];
  }
  if (os === "macos" && release.assets.macos.length > 0) {
    return release.assets.macos[0];
  }
  return null;
}
