import { notFound } from "next/navigation";
import Link from "next/link";
import { getReleaseByVersion, getReleases } from "@/data/releases";
import { Calendar, Download, ArrowLeft, CheckCircle2, ShieldCheck, FileText, AlertTriangle } from "lucide-react";

interface ReleasePageProps {
  params: {
    version: string;
  };
}

export function generateStaticParams() {
  return getReleases().map((r) => ({
    version: r.version,
  }));
}

export function generateMetadata({ params }: ReleasePageProps) {
  const release = getReleaseByVersion(params.version);
  if (!release) return { title: "Release Not Found" };

  return {
    title: `Photo Face Organizer ${release.version} Release Notes & Downloads`,
    description: `Full release notes, downloads, and package details for Photo Face Organizer ${release.version}.`,
  };
}

export default function ReleaseDetailPage({ params }: ReleasePageProps) {
  const release = getReleaseByVersion(params.version);

  if (!release) {
    notFound();
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-10">
      {/* Back Button */}
      <Link
        href="/releases"
        className="inline-flex items-center gap-2 text-sm font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Back to All Releases</span>
      </Link>

      {/* Title Header */}
      <div className="p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white">
            Photo Face Organizer {release.version}
          </h1>
          {release.isLatest && (
            <span className="px-3 py-1 rounded-full bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 text-xs font-semibold">
              Latest Release
            </span>
          )}
        </div>
        <p className="text-sm text-slate-500 flex items-center gap-2">
          <Calendar className="w-4 h-4" />
          <span>Released on {release.releaseDate}</span>
        </p>
        <h2 className="text-xl font-bold text-slate-800 dark:text-slate-200 pt-2">
          {release.title}
        </h2>
      </div>

      {/* Release Highlights */}
      <div className="p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-4">
        <h3 className="text-lg font-bold text-slate-900 dark:text-white">
          Release Highlights &amp; Improvements
        </h3>
        <ul className="space-y-3 text-sm text-slate-700 dark:text-slate-300">
          {release.highlights.map((item, idx) => (
            <li key={idx} className="flex items-start gap-2.5">
              <CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0 mt-0.5" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Release Notes */}
      <div className="p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-4">
        <h3 className="text-lg font-bold text-slate-900 dark:text-white">
          Detailed Technical Notes
        </h3>
        <div className="space-y-2 text-sm text-slate-600 dark:text-slate-400">
          {release.notes.map((note, idx) => (
            <p key={idx}>{note}</p>
          ))}
        </div>
      </div>

      {/* Package Downloads & Checksums */}
      <div className="p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-6">
        <h3 className="text-lg font-bold text-slate-900 dark:text-white">
          Available Download Packages &amp; SHA256 Checksums
        </h3>

        <div className="space-y-4">
          {[
            ...release.assets.linux,
            ...release.assets.windows,
            ...release.assets.macos,
          ].map((asset, idx) => (
            <div
              key={idx}
              className="p-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/50 space-y-2"
            >
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div>
                  <h4 className="font-bold text-sm text-slate-900 dark:text-white">
                    {asset.name}
                  </h4>
                  <p className="text-xs font-mono text-slate-500">
                    {asset.filename} ({asset.size})
                  </p>
                </div>

                {asset.available ? (
                  <a
                    href={asset.url}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-700 text-white text-xs font-medium transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download File</span>
                  </a>
                ) : (
                  <span className="text-xs px-3 py-1.5 rounded-xl bg-slate-200 dark:bg-slate-800 text-slate-500 font-medium">
                    Unavailable
                  </span>
                )}
              </div>

              {asset.sha256 && (
                <div className="pt-2 border-t border-slate-200 dark:border-slate-800/80 text-[11px] font-mono text-slate-500 break-all">
                  SHA256: {asset.sha256}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Known Issues (if any) */}
      {release.knownIssues && release.knownIssues.length > 0 && (
        <div className="p-6 rounded-2xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900 text-amber-800 dark:text-amber-200 text-sm space-y-2">
          <div className="font-bold flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            <span>Known Issues &amp; Limitations</span>
          </div>
          <ul className="list-disc list-inside space-y-1 text-xs">
            {release.knownIssues.map((issue, idx) => (
              <li key={idx}>{issue}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
