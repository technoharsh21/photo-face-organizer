import Link from "next/link";
import { DownloadButton } from "@/components/DownloadButton";
import { getLatestRelease } from "@/data/releases";
import {
  ShieldCheck,
  Cpu,
  FolderLock,
  Users,
  Sparkles,
  Zap,
  ArrowRight,
  CheckCircle2,
  HardDrive,
  UserPlus,
  Image as ImageIcon,
  FolderOutput,
  Play,
  CheckCheck,
  Monitor,
  Terminal,
  Apple,
  Star,
  Copy,
  Layers,
} from "lucide-react";

export default function HomePage() {
  const latestRelease = getLatestRelease();

  return (
    <div className="space-y-24 pb-20">
      {/* HERO SECTION */}
      <section className="relative pt-12 lg:pt-20 pb-16 overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto space-y-6">
            {/* Version Badge */}
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-brand-200 dark:border-brand-900 bg-brand-50 dark:bg-brand-950/60 text-brand-700 dark:text-brand-300 text-xs font-semibold">
              <Sparkles className="w-3.5 h-3.5 text-brand-500" />
              <span>Latest Version {latestRelease.version} Released</span>
            </div>

            {/* Headline */}
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-slate-900 dark:text-white tracking-tight leading-[1.15]">
              Find your people. Organize your photos.{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-600 to-blue-500 dark:from-brand-400 dark:to-cyan-400">
                Keep everything local.
              </span>
            </h1>

            {/* Subtitle */}
            <p className="text-lg sm:text-xl text-slate-600 dark:text-slate-300 leading-relaxed">
              Photo Face Organizer uses local AI face recognition and universal GPU acceleration to automatically scan your photos, isolate solo portraits, find duplicate images, and organize memories safely without cloud uploads.
            </p>

            {/* Hero CTAs */}
            <div className="pt-4 flex flex-col items-center justify-center gap-4">
              <DownloadButton />

              <div className="flex flex-wrap items-center justify-center gap-6 text-sm text-slate-600 dark:text-slate-400 pt-2">
                <Link
                  href="/docs/installation"
                  className="inline-flex items-center gap-1.5 hover:text-slate-900 dark:hover:text-white transition-colors underline underline-offset-4"
                >
                  <span>View Installation Guide</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
                <span>•</span>
                <Link
                  href="/releases"
                  className="inline-flex items-center gap-1.5 hover:text-slate-900 dark:hover:text-white transition-colors underline underline-offset-4"
                >
                  <span>View All Releases ({latestRelease.version})</span>
                </Link>
              </div>
            </div>

            {/* Quick Guarantees */}
            <div className="pt-8 grid grid-cols-2 md:grid-cols-4 gap-4 text-left border-t border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-2 text-xs font-medium text-slate-700 dark:text-slate-300">
                <ShieldCheck className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                <span>100% Local Privacy</span>
              </div>
              <div className="flex items-center gap-2 text-xs font-medium text-slate-700 dark:text-slate-300">
                <Cpu className="w-4 h-4 text-amber-500 flex-shrink-0" />
                <span>Universal GPU Acceleration</span>
              </div>
              <div className="flex items-center gap-2 text-xs font-medium text-slate-700 dark:text-slate-300">
                <Users className="w-4 h-4 text-purple-500 flex-shrink-0" />
                <span>Solo &amp; Group Precision</span>
              </div>
              <div className="flex items-center gap-2 text-xs font-medium text-slate-700 dark:text-slate-300">
                <Star className="w-4 h-4 text-brand-500 flex-shrink-0" />
                <span>4/5-Star Quality Gates</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* KEY BENEFITS */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 className="text-3xl font-extrabold text-slate-900 dark:text-white">
            Designed for Privacy, Speed, and Peace of Mind
          </h2>
          <p className="mt-3 text-slate-600 dark:text-slate-400">
            Organize thousands of memory photos automatically without sacrificing privacy or risking file corruption.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[
            {
              icon: <Cpu className="w-6 h-6 text-amber-500" />,
              title: "Universal GPU Acceleration",
              desc: "Auto-binds to DirectX 12 DirectML (NVIDIA/AMD/Intel), CUDA, TensorRT, ROCm, Apple Neural Engine CoreML, or Multi-Core CPU.",
            },
            {
              icon: <Sparkles className="w-6 h-6 text-brand-500" />,
              title: "Solo Photo Scanning",
              desc: "Isolates pure single-person and couple portraits with 360° profile face detection and secondary deep exclusion scans.",
            },
            {
              icon: <Copy className="w-6 h-6 text-blue-500" />,
              title: "Cryptographic Duplicate Finder",
              desc: "Finds 100% byte-for-byte duplicate photos at multi-GB/s speed using hardware-accelerated CPU SHA-256 hashing.",
            },
            {
              icon: <Star className="w-6 h-6 text-emerald-500" />,
              title: "4 & 5-Star Quality Gates",
              desc: "Multi-dimensional scoring evaluates resolution, Laplacian focus sharpness, and lighting to reject blurry low-quality faces.",
            },
            {
              icon: <FolderLock className="w-6 h-6 text-indigo-500" />,
              title: "100% Non-Destructive",
              desc: "Your original photo library is never modified. Photos are safely copied with automatic collision and file audit reconciliation.",
            },
            {
              icon: <Users className="w-6 h-6 text-purple-500" />,
              title: "Compulsory Group Photos",
              desc: "Group profiles require ALL compulsory individuals to appear together in a photo before routing into shared albums.",
            },
            {
              icon: <Layers className="w-6 h-6 text-pink-500" />,
              title: "1-Click Clean Outliers",
              desc: "Instantly purges wrong identities and degraded low-star photos to maintain a pristine, high-precision reference database.",
            },
            {
              icon: <ShieldCheck className="w-6 h-6 text-teal-500" />,
              title: "5-Point Landmark Geometry",
              desc: "Validates anatomical eye-to-nose geometry to guarantee 0% false detections from t-shirts, patterns, or statues.",
            },
          ].map((benefit, idx) => (
            <div
              key={idx}
              className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="p-2.5 rounded-xl bg-slate-100 dark:bg-slate-800 w-fit mb-4">
                {benefit.icon}
              </div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">
                {benefit.title}
              </h3>
              <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                {benefit.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* HOW IT WORKS VISUAL FLOW */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 bg-slate-100 dark:bg-slate-900/40 rounded-3xl p-8 sm:p-12 border border-slate-200 dark:border-slate-800">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 className="text-3xl font-extrabold text-slate-900 dark:text-white">
            How Photo Face Organizer Works
          </h2>
          <p className="mt-3 text-slate-600 dark:text-slate-400">
            A simple, intuitive 6-step workflow designed for total control.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4 relative">
          {[
            {
              step: "01",
              icon: <UserPlus className="w-5 h-5 text-brand-500" />,
              title: "Create Profiles",
              desc: "Define individual or group profiles.",
            },
            {
              step: "02",
              icon: <ImageIcon className="w-5 h-5 text-purple-500" />,
              title: "Add References",
              desc: "Upload 4/5-star reference photos.",
            },
            {
              step: "03",
              icon: <HardDrive className="w-5 h-5 text-blue-500" />,
              title: "Select Sources",
              desc: "Choose photo folders to scan.",
            },
            {
              step: "04",
              icon: <FolderOutput className="w-5 h-5 text-amber-500" />,
              title: "Choose Output",
              desc: "Set target output directory.",
            },
            {
              step: "05",
              icon: <Play className="w-5 h-5 text-emerald-500" />,
              title: "Start Scan",
              desc: "AI recognizes and routes photos.",
            },
            {
              step: "06",
              icon: <CheckCheck className="w-5 h-5 text-teal-500" />,
              title: "Organized Copies",
              desc: "Photos copied safely by person.",
            },
          ].map((item, idx) => (
            <div
              key={idx}
              className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center space-y-3 relative"
            >
              <div className="text-xs font-mono font-bold text-brand-600 dark:text-brand-400">
                STEP {item.step}
              </div>
              <div className="p-2 rounded-xl bg-slate-100 dark:bg-slate-800 w-fit mx-auto">
                {item.icon}
              </div>
              <h4 className="font-bold text-sm text-slate-900 dark:text-white">
                {item.title}
              </h4>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {item.desc}
              </p>
            </div>
          ))}
        </div>

        <div className="mt-8 p-4 rounded-xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900 text-blue-800 dark:text-blue-200 text-sm text-center">
          💡 <strong>Multi-Person Copy Rule:</strong> If a photo contains both Alice and Bob, it is automatically copied into <code>Output/Alice/</code>, <code>Output/Bob/</code>, AND <code>Output/Alice &amp; Bob/</code> without deleting or moving the original file.
        </div>
      </section>

      {/* FEATURE SHOWCASE */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-16">
        <div className="text-center max-w-2xl mx-auto">
          <h2 className="text-3xl font-extrabold text-slate-900 dark:text-white">
            Feature Showcase
          </h2>
          <p className="mt-3 text-slate-600 dark:text-slate-400">
            Engineered with strict safety standards, multi-architecture GPU engines, and flexible matching logic.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Card 1 */}
          <div className="p-8 rounded-3xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-4">
            <div className="p-3 rounded-2xl bg-brand-50 dark:bg-brand-950/60 text-brand-600 w-fit">
              <Cpu className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold text-slate-900 dark:text-white">
              Universal GPU Acceleration Engine
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
              Utilizes 512-dimensional ArcFace facial embedding vectors generated via local neural networks. Automatically binds to DirectML (Windows all GPUs), CUDA / TensorRT (NVIDIA), ROCm (AMD), CoreML (Apple Silicon), or OpenVINO (Intel).
            </p>
            <ul className="space-y-2 text-xs text-slate-700 dark:text-slate-300">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span>100% compute saturation with concurrent worker pipelines</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span>Zero-crash fallback to multi-core CPU execution</span>
              </li>
            </ul>
          </div>

          {/* Card 2 */}
          <div className="p-8 rounded-3xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-4">
            <div className="p-3 rounded-2xl bg-purple-50 dark:bg-purple-950/60 text-purple-600 w-fit">
              <Sparkles className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold text-slate-900 dark:text-white">
              Precision Solo Photo Scanning
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
              Create pure solo albums containing only the target individual. Features SCRFD 360° multi-angle detection (90° side profiles) and automatic 2-stage deep background exclusion verification.
            </p>
            <ul className="space-y-2 text-xs text-slate-700 dark:text-slate-300">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span>Exclusive couple solo mode (exact 2-person matching, 0% strangers)</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span>Dominant subject portrait framing &amp; photobomber crowd control</span>
              </li>
            </ul>
          </div>

          {/* Card 3 */}
          <div className="p-8 rounded-3xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-4">
            <div className="p-3 rounded-2xl bg-blue-50 dark:bg-blue-950/60 text-blue-600 w-fit">
              <Copy className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold text-slate-900 dark:text-white">
              Cryptographic Duplicate Photos Finder
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
              Instantly identify 100% byte-for-byte identical photos using a 3-tier CPU hashing pipeline (instant file-size pre-filtering + hardware SHA-256 hashing).
            </p>
            <ul className="space-y-2 text-xs text-slate-700 dark:text-slate-300">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span>Smart 1-click selection rules (keep oldest, newest, or shortest path)</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span>Safe cleanup via OS Recycle Bin / Trash or quarantine folders</span>
              </li>
            </ul>
          </div>

          {/* Card 4 */}
          <div className="p-8 rounded-3xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-4">
            <div className="p-3 rounded-2xl bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 w-fit">
              <Star className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-bold text-slate-900 dark:text-white">
              4 &amp; 5-Star Quality Gates &amp; Clean Outliers
            </h3>
            <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
              Every face is evaluated on resolution, focus sharpness (Laplacian variance), and lighting. Enforces strict 4 &amp; 5-star quality standards on reference photos and Unknown Face conversions.
            </p>
            <ul className="space-y-2 text-xs text-slate-700 dark:text-slate-300">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span>🧹 1-Click &quot;Clean Outliers&quot; purges wrong identities &amp; blurry photos</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span>5-Point landmark geometry rejects non-human texture artifacts</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* SUPPORTED PLATFORMS */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <h2 className="text-3xl font-extrabold text-slate-900 dark:text-white">
            Supported Operating Systems
          </h2>
          <p className="mt-3 text-slate-600 dark:text-slate-400">
            Native packages and standalone bundles available across platforms.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Linux Card */}
          <div className="p-8 rounded-3xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-6">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-2xl bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white">
                <Terminal className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-slate-900 dark:text-white">Linux</h3>
                <p className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">Fully Supported</p>
              </div>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Debian/Ubuntu <code>.deb</code> package, Standalone ZIP bundle, and PyPI <code>pip install</code>.
            </p>
            <div className="space-y-2 pt-2">
              <Link
                href="/download"
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium transition-colors"
              >
                <span>Download Linux Assets</span>
              </Link>
              <Link
                href="/docs/installation/linux"
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
              >
                <span>Linux Setup Guide &rarr;</span>
              </Link>
            </div>
          </div>

          {/* Windows Card */}
          <div className="p-8 rounded-3xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-6">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-2xl bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white">
                <Monitor className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-slate-900 dark:text-white">Windows</h3>
                <p className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">Fully Supported</p>
              </div>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Windows Setup Installer (Inno Setup <code>.exe</code> wizard with DirectML GPU acceleration).
            </p>
            <div className="space-y-2 pt-2">
              <Link
                href="/download"
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium transition-colors"
              >
                <span>Download Windows Installer</span>
              </Link>
              <Link
                href="/docs/installation/windows"
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2 text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
              >
                <span>Windows Setup Guide &rarr;</span>
              </Link>
            </div>
          </div>

          {/* macOS Card */}
          <div className="p-8 rounded-3xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-6">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-2xl bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white">
                <Apple className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-slate-900 dark:text-white">macOS</h3>
                <p className="text-xs text-amber-600 dark:text-amber-400 font-medium">Run from Source / Pip</p>
              </div>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              macOS standalone <code>.dmg</code> build with Apple Neural Engine CoreML acceleration.
            </p>
            <div className="space-y-2 pt-2">
              <Link
                href="/docs/installation/macos"
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white text-sm font-medium hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
              >
                <span>macOS Setup Guide</span>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* FINAL DOWNLOAD CTA */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="p-10 sm:p-14 rounded-3xl bg-gradient-to-br from-brand-600 to-blue-700 text-white text-center space-y-6 shadow-xl">
          <h2 className="text-3xl sm:text-4xl font-extrabold">
            Ready to Organize Your Photo Library?
          </h2>
          <p className="text-brand-100 max-w-2xl mx-auto text-base sm:text-lg">
            Download Photo Face Organizer today. Free, open-source, and 100% local.
          </p>

          <div className="pt-2 flex flex-col items-center justify-center gap-4">
            <DownloadButton />
          </div>

          <div className="text-xs text-brand-200 pt-4 flex items-center justify-center gap-4">
            <span>Version {latestRelease.version}</span>
            <span>•</span>
            <span>Released {latestRelease.releaseDate}</span>
            <span>•</span>
            <Link href="/releases" className="underline hover:text-white">
              Release History
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
