export interface DocNavItem {
  title: string;
  href: string;
  category: string;
  description: string;
}

export const DOCS_NAV: DocNavItem[] = [
  {
    title: "Getting Started",
    href: "/docs/getting-started",
    category: "Overview",
    description: "Learn the core workflow of Photo Face Organizer."
  },
  {
    title: "Installation Overview",
    href: "/docs/installation",
    category: "Installation",
    description: "General setup instructions for all platforms."
  },
  {
    title: "Linux Setup (.deb & Pip)",
    href: "/docs/installation/linux",
    category: "Installation",
    description: "Install via Debian package, pipx, or standalone bundle."
  },
  {
    title: "Windows Setup (.exe)",
    href: "/docs/installation/windows",
    category: "Installation",
    description: "Install using the Windows Inno Setup wizard."
  },
  {
    title: "macOS Setup (.dmg)",
    href: "/docs/installation/macos",
    category: "Installation",
    description: "macOS installation and Gatekeeper verification."
  },
  {
    title: "Profiles & Reference Photos",
    href: "/docs/profiles",
    category: "Usage Guide",
    description: "Creating person profiles and adding reference faces."
  },
  {
    title: "Scanning & Matching Rules",
    href: "/docs/scanning",
    category: "Usage Guide",
    description: "Folder selection, recursive scanning, and match thresholds."
  },
  {
    title: "Solo Photo Scanning",
    href: "/docs/solo-scan",
    category: "Usage Guide",
    description: "Single-person pure albums, profile-angle detection, and couple solo scanning."
  },
  {
    title: "Group Photos & Profiles",
    href: "/docs/group-photos",
    category: "Usage Guide",
    description: "Multi-person routing and compulsory group profile matching."
  },
  {
    title: "Find Photos by Person",
    href: "/docs/find-photos",
    category: "Usage Guide",
    description: "Real-time discovery of any person's photos across folders, with Solo vs All matching."
  },
  {
    title: "Duplicate Photos Finder",
    href: "/docs/duplicates",
    category: "Usage Guide",
    description: "Fast cryptographic SHA-256 duplicate scanning and safe cleanup."
  },
  {
    title: "Unknown Faces Management",
    href: "/docs/unknown-faces",
    category: "Usage Guide",
    description: "Inspecting unmatched faces and converting face clusters."
  },
  {
    title: "Live Camera Face Enrollment",
    href: "/docs/live-enrollment",
    category: "Usage Guide",
    description: "Hands-free 360° webcam capture of 5 face angles to train a new profile."
  },
  {
    title: "Photo Viewer & Lightbox",
    href: "/docs/photo-viewer",
    category: "Usage Guide",
    description: "Zoom, rotate, and browse matched photos with full keyboard navigation."
  },
  {
    title: "Results, Audit & Corrections",
    href: "/docs/results-audit",
    category: "Usage Guide",
    description: "File reconciliation audit, output tree, skipped-file export, and match corrections."
  },
  {
    title: "Scan History & Crash Recovery",
    href: "/docs/history",
    category: "Usage Guide",
    description: "Resume interrupted scans, review past runs, and manage history records."
  },
  {
    title: "Quality Ratings & Outliers",
    href: "/docs/quality-ratings",
    category: "Usage Guide",
    description: "4/5-star multi-factor quality scoring and 1-click outlier cleaning."
  },
  {
    title: "Settings & Face Cache",
    href: "/docs/settings",
    category: "Configuration",
    description: "Performance profiles, hardware preference, matching threshold, and the face embedding cache."
  },
  {
    title: "Hardware & Acceleration",
    href: "/docs/hardware",
    category: "Performance",
    description: "Universal GPU acceleration (DirectML, CUDA, ROCm, CoreML, OpenVINO) and CPU."
  },
  {
    title: "Privacy & File Safety",
    href: "/docs/privacy-data",
    category: "Architecture",
    description: "Local-first data storage and non-destructive file routing."
  }
];
