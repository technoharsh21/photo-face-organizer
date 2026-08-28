import Link from "next/link";
import { DownloadButton } from "@/components/DownloadButton";
import { CommandBlock } from "@/components/CommandBlock";
import { getLatestRelease } from "@/data/releases";
import {
  Download,
  Terminal,
  Monitor,
  Apple,
  CheckCircle2,
  FileText,
  ShieldCheck,
  ArrowRight,
  Info,
  Clock,
} from "lucide-react";

export const metadata = {
  title: "Download Photo Face Organizer | Windows, Linux, macOS",
  description:
    "Download the latest release of Photo Face Organizer. Native .deb packages, Windows setup installers, standalone zip archives, and pip install instructions.",
};

export default function DownloadPage() {
  const latestRelease = getLatestRelease();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-12">
      {/* Header */}
      <div className="text-center max-w-3xl mx-auto space-y-4">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-50 dark:bg-brand-950/60 border border-brand-200 dark:border-brand-900 text-brand-700 dark:text-brand-300 text-xs font-semibold">
          <Clock className="w-3.5 h-3.5" />
          <span>Latest Release: {latestRelease.version} ({latestRelease.releaseDate})</span>
        </div>
        <h1 className="text-4xl font-extrabold text-slate-900 dark:text-white">
          Download Photo Face Organizer
        </h1>
        <p className="text-slate-600 dark:text-slate-400 text-base sm:text-lg">
          Select your platform below to download the official desktop installer or standalone package.
        </p>
      </div>

      {/* Smart OS Download Section */}
      <div className="p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="space-y-2 text-center md:text-left">
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
            Official Stable Release {latestRelease.version}
          </h2>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Smart system detection automatically recommends the appropriate download format for your computer.
          </p>
        </div>

        <DownloadButton />
      </div>

      {/* Release Highlights */}
      <div className="p-6 rounded-2xl bg-slate-100 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 space-y-4">
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-900 dark:text-white flex items-center gap-2">
          <SparklesIcon className="w-4 h-4 text-brand-500" />
          <span>What&apos;s New in {latestRelease.version}</span>
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm text-slate-700 dark:text-slate-300">
          {latestRelease.highlights.map((item, idx) => (
            <div key={idx} className="flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
              <span>{item}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Platform Assets Table */}
      <div className="space-y-8">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
          All Platform Assets &amp; Package Downloads
        </h2>

        {/* LINUX SECTION */}
        <div className="p-6 sm:p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white">
                <Terminal className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">Linux Packages</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">Debian, Ubuntu, Mint, Fedora &amp; Arch</p>
              </div>
            </div>
            <Link
              href="/docs/installation/linux"
              className="text-xs font-medium text-brand-600 dark:text-brand-400 hover:underline"
            >
              Linux Setup Docs &rarr;
            </Link>
          </div>

          <div className="space-y-4">
            {latestRelease.assets.linux.map((asset, idx) => (
              <div
                key={idx}
                className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/50 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-slate-900 dark:text-white">
                      {asset.name}
                    </span>
                    {asset.architecture && (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                        {asset.architecture}
                      </span>
                    )}
                  </div>
                  <p className="text-xs font-mono text-slate-500">{asset.filename} ({asset.size})</p>
                  {asset.notes && <p className="text-xs text-slate-600 dark:text-slate-400">{asset.notes}</p>}
                </div>

                {asset.available ? (
                  <a
                    href={asset.url}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-xs font-medium transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download</span>
                  </a>
                ) : (
                  <span className="text-xs px-3 py-1.5 rounded-lg bg-slate-200 dark:bg-slate-800 text-slate-500 font-medium">
                    Not Available
                  </span>
                )}
              </div>
            ))}
          </div>

          <div className="pt-2">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
              Command-Line Pip Installation (Any Linux Distro)
            </h4>
            <CommandBlock
              command="pip install git+https://github.com/technoharsh21/photo-face-organizer.git"
              language="bash"
            />
          </div>
        </div>

        {/* WINDOWS SECTION */}
        <div className="p-6 sm:p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white">
                <Monitor className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">Windows Installer</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">Windows 10 / 11 (64-bit)</p>
              </div>
            </div>
            <Link
              href="/docs/installation/windows"
              className="text-xs font-medium text-brand-600 dark:text-brand-400 hover:underline"
            >
              Windows Setup Docs &rarr;
            </Link>
          </div>

          <div className="space-y-4">
            {latestRelease.assets.windows.map((asset, idx) => (
              <div
                key={idx}
                className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/50 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-slate-900 dark:text-white">
                      {asset.name}
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                      {asset.architecture}
                    </span>
                  </div>
                  <p className="text-xs font-mono text-slate-500">{asset.filename} ({asset.size})</p>
                  {asset.notes && <p className="text-xs text-slate-600 dark:text-slate-400">{asset.notes}</p>}
                </div>

                {asset.available ? (
                  <a
                    href={asset.url}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-xs font-medium transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download Installer</span>
                  </a>
                ) : (
                  <span className="text-xs px-3 py-1.5 rounded-lg bg-slate-200 dark:bg-slate-800 text-slate-500 font-medium">
                    Not Available
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* MACOS SECTION */}
        <div className="p-6 sm:p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white">
                <Apple className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">macOS Assets</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">Apple Silicon (M1/M2/M3) &amp; Intel</p>
              </div>
            </div>
            <Link
              href="/docs/installation/macos"
              className="text-xs font-medium text-brand-600 dark:text-brand-400 hover:underline"
            >
              macOS Setup Docs &rarr;
            </Link>
          </div>

          <div className="space-y-4">
            {latestRelease.assets.macos.map((asset, idx) => (
              <div
                key={idx}
                className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/50 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 opacity-80"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-slate-900 dark:text-white">
                      {asset.name}
                    </span>
                  </div>
                  <p className="text-xs font-mono text-slate-500">{asset.filename}</p>
                  {asset.notes && <p className="text-xs text-amber-600 dark:text-amber-400">{asset.notes}</p>}
                </div>

                <span className="text-xs px-3 py-1.5 rounded-lg bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 font-medium flex items-center gap-1.5">
                  <Info className="w-3.5 h-3.5" />
                  <span>Run via Pip</span>
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Previous Releases Link Footer */}
      <div className="pt-6 text-center border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-slate-600 dark:text-slate-400">
        <div>
          Looking for older versions or complete changelogs?
        </div>
        <Link
          href="/releases"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white font-medium hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
        >
          <FileText className="w-4 h-4" />
          <span>View Release History</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  );
}

function SparklesIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg fill="currentColor" viewBox="0 0 24 24" {...props}>
      <path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z" />
    </svg>
  );
}
