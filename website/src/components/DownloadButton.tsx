"use client";

import { useState } from "react";
import { useOS } from "@/hooks/useOS";
import { getLatestRelease, SupportedOS, getPrimaryAssetForOS } from "@/data/releases";
import { Download, ChevronDown, Check, Monitor, Terminal, Apple } from "lucide-react";

export function DownloadButton() {
  const { os, isDetected } = useOS();
  const [selectedOS, setSelectedOS] = useState<SupportedOS | null>(null);
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const release = getLatestRelease();
  const activeOS = selectedOS || (isDetected && os !== "unknown" ? os : "linux");

  const activeAsset = getPrimaryAssetForOS(release, activeOS);

  const getOSLabel = (targetOS: SupportedOS) => {
    switch (targetOS) {
      case "windows":
        return "Windows";
      case "linux":
        return "Linux";
      case "macos":
        return "macOS";
      default:
        return "All Platforms";
    }
  };

  const getOSIcon = (targetOS: SupportedOS) => {
    switch (targetOS) {
      case "windows":
        return <Monitor className="w-4 h-4" />;
      case "linux":
        return <Terminal className="w-4 h-4" />;
      case "macos":
        return <Apple className="w-4 h-4" />;
      default:
        return <Download className="w-4 h-4" />;
    }
  };

  return (
    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
      {/* Primary Action Button */}
      {activeAsset && activeAsset.available ? (
        <a
          href={activeAsset.url}
          className="inline-flex items-center justify-center gap-2.5 px-6 py-3.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-semibold shadow-md shadow-brand-500/20 transition-all hover:scale-[1.02] focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          {getOSIcon(activeOS)}
          <span>Download for {getOSLabel(activeOS)}</span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-brand-700/60 font-mono">
            {release.version}
          </span>
        </a>
      ) : (
        <div className="inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-slate-200 dark:bg-slate-800 text-slate-500 dark:text-slate-400 font-semibold cursor-not-allowed">
          <span>Not Available for {getOSLabel(activeOS)}</span>
        </div>
      )}

      {/* Manual OS Dropdown Selector */}
      <div className="relative">
        <button
          onClick={() => setDropdownOpen(!dropdownOpen)}
          className="w-full sm:w-auto inline-flex items-center justify-between sm:justify-start gap-2 px-4 py-3.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500"
          aria-label="Select platform manually"
        >
          <span className="flex items-center gap-2">
            {getOSIcon(activeOS)}
            <span>{getOSLabel(activeOS)}</span>
          </span>
          <ChevronDown className="w-4 h-4 text-slate-400" />
        </button>

        {dropdownOpen && (
          <div className="absolute left-0 right-0 sm:right-auto sm:w-48 mt-2 py-1.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xl z-20">
            <div className="px-3 py-1.5 text-[10px] font-semibold tracking-wider uppercase text-slate-400">
              Select Platform
            </div>
            {(["windows", "linux", "macos"] as SupportedOS[]).map((platform) => (
              <button
                key={platform}
                onClick={() => {
                  setSelectedOS(platform);
                  setDropdownOpen(false);
                }}
                className={`w-full flex items-center justify-between px-3 py-2 text-sm text-left ${
                  activeOS === platform
                    ? "bg-brand-50 dark:bg-brand-950/40 text-brand-600 dark:text-brand-400 font-medium"
                    : "text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                }`}
              >
                <span className="flex items-center gap-2">
                  {getOSIcon(platform)}
                  <span>{getOSLabel(platform)}</span>
                </span>
                {activeOS === platform && <Check className="w-4 h-4 text-brand-600 dark:text-brand-400" />}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
