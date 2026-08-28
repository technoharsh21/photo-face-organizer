import Link from "next/link";
import { getReleases } from "@/data/releases";
import { Tag, Calendar, Download, ArrowRight, CheckCircle2, ShieldAlert } from "lucide-react";

export const metadata = {
  title: "Release History & Changelogs | Photo Face Organizer",
  description:
    "Explore the complete release history, version notes, changelogs, and package downloads for Photo Face Organizer.",
};

export default function ReleasesPage() {
  const releases = getReleases();

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-10">
      {/* Header */}
      <div className="space-y-4">
        <h1 className="text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight">
          Release History &amp; Version Notes
        </h1>
        <p className="text-slate-600 dark:text-slate-400 text-base max-w-3xl">
          Detailed changelogs, new features, bug fixes, and download packages for all current and past releases of Photo Face Organizer.
        </p>
      </div>

      {/* Releases List */}
      <div className="space-y-8">
        {releases.map((release) => (
          <div
            key={release.version}
            className="p-6 sm:p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm space-y-6"
          >
            {/* Version Header */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
              <div className="flex items-center gap-3">
                <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
                  {release.version}
                </h2>
                {release.isLatest && (
                  <span className="px-3 py-1 rounded-full bg-emerald-100 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 text-xs font-semibold">
                    Latest Release
                  </span>
                )}
                <span className="text-sm text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                  <Calendar className="w-4 h-4" />
                  <span>{release.releaseDate}</span>
                </span>
              </div>

              <Link
                href={`/releases/${release.version}`}
                className="inline-flex items-center gap-1.5 text-sm font-medium text-brand-600 dark:text-brand-400 hover:underline"
              >
                <span>Full Release Notes &amp; Checksums</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>

            {/* Title & Highlights */}
            <div className="space-y-3">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                {release.title}
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm text-slate-600 dark:text-slate-300">
                {release.highlights.map((item, idx) => (
                  <div key={idx} className="flex items-start gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Download Buttons Summary */}
            <div className="pt-4 flex flex-wrap items-center gap-3">
              {release.assets.linux.map((asset, idx) => (
                asset.available && (
                  <a
                    key={idx}
                    href={asset.url}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-900 dark:text-white text-xs font-medium transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Linux ({asset.type.toUpperCase()})</span>
                  </a>
                )
              ))}
              {release.assets.windows.map((asset, idx) => (
                asset.available && (
                  <a
                    key={idx}
                    href={asset.url}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-900 dark:text-white text-xs font-medium transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Windows (.exe)</span>
                  </a>
                )
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
