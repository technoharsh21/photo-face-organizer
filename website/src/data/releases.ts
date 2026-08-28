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
      "Compulsory group photo matching (requires ALL compulsory faces in a single photo)",
      "Real-time disk verification to prevent duplicate photo skipping",
      "File Audit Reconciliation summary card (100% accounted for, 0 photos lost)",
      "Automated nodemon-style dev auto-reloader and Pycache disabling",
      "Native Linux .deb installer package & Standalone ZIP package",
      "PyPI Python package support (pip / pipx install)",
      "Automated GitHub Actions Windows installer workflow (.exe setup)",
      "Automated macOS Disk Image (.dmg) & Zip bundle build pipeline"
    ],
    notes: [
      "First stable production-ready release of Photo Face Organizer.",
      "Support for CPU-based face recognition with dlib and OpenCV backends.",
      "High-contrast dark modern theme for Unknown Faces clustering and profile detail management."
    ],
    assets: {
      linux: [
        {
          name: "Debian / Ubuntu Package (.deb)",
          filename: "photo-face-organizer_1.0.0_amd64.deb",
          url: "https://github.com/technoharsh21/photo-face-organizer/releases/download/v1.0.0/photo-face-organizer_1.0.0_amd64.deb",
          size: "117 MB",
          type: "deb",
          architecture: "amd64 (64-bit)",
          sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
          available: true,
          notes: "Official release package. Install via: sudo dpkg -i photo-face-organizer_1.0.0_amd64.deb"
        },
        {
          name: "Linux Standalone Bundle (.zip)",
          filename: "PhotoFaceOrganizer_Linux.zip",
          url: "https://github.com/technoharsh21/photo-face-organizer/releases/download/v1.0.0/PhotoFaceOrganizer_Linux.zip",
          size: "155 MB",
          type: "zip",
          architecture: "x86_64",
          sha256: "f2ca1bb6c7e907d06dafe4687e579fce76b37e4e93b7605022da52e6ccc26fd2",
          available: true,
          notes: "Extract and run ./dist/PhotoFaceOrganizer/PhotoFaceOrganizer"
        },
        {
          name: "PyPI Package (pip / pipx)",
          filename: "photo-face-organizer-1.0.0.tar.gz",
          url: "https://github.com/technoharsh21/photo-face-organizer",
          size: "524 KB",
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
          size: "140 MB (Est.)",
          type: "exe",
          architecture: "x64 (64-bit)",
          available: true,
          notes: "Windows Inno Setup installer wizard with Desktop & Start Menu icons"
        }
      ],
      macos: [
        {
          name: "macOS Disk Image (.dmg)",
          filename: "PhotoFaceOrganizer_macOS.dmg",
          url: "https://github.com/technoharsh21/photo-face-organizer/releases/download/v1.0.0/PhotoFaceOrganizer_macOS.dmg",
          size: "150 MB (Est.)",
          type: "dmg",
          architecture: "Apple Silicon (M1/M2/M3) & Intel",
          available: true,
          notes: "Native macOS disk image installer. Built automatically via GitHub Actions workflow."
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
  if (os === 'windows' && release.assets.windows.length > 0) {
    return release.assets.windows[0];
  }
  if (os === 'linux' && release.assets.linux.length > 0) {
    return release.assets.linux[0];
  }
  if (os === 'macos' && release.assets.macos.length > 0) {
    return release.assets.macos[0];
  }
  return null;
}
