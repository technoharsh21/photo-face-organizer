import Link from "next/link";
import { Terminal, Monitor, Apple, ArrowRight } from "lucide-react";

export const metadata = {
  title: "Installation Overview | Photo Face Organizer Docs",
  description: "Cross-platform installation hub for Linux, Windows, and macOS.",
};

export default function InstallationOverviewPage() {
  return (
    <div className="space-y-8 text-slate-700 dark:text-slate-300">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-6 space-y-2">
        <span className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
          Installation
        </span>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
          Installation Overview
        </h1>
        <p className="text-sm text-slate-500">
          Photo Face Organizer provides native installation packages and command-line options for Linux, Windows, and macOS.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        <Link
          href="/docs/installation/linux"
          className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-brand-500 transition-colors space-y-3"
        >
          <Terminal className="w-6 h-6 text-brand-500" />
          <h3 className="font-bold text-slate-900 dark:text-white">Linux</h3>
          <p className="text-xs text-slate-500">
            Debian <code>.deb</code> package, standalone ZIP, and <code>pip install</code>.
          </p>
          <span className="text-xs font-medium text-brand-600 flex items-center gap-1">
            <span>Read Guide</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </span>
        </Link>

        <Link
          href="/docs/installation/windows"
          className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-brand-500 transition-colors space-y-3"
        >
          <Monitor className="w-6 h-6 text-blue-500" />
          <h3 className="font-bold text-slate-900 dark:text-white">Windows</h3>
          <p className="text-xs text-slate-500">
            Inno Setup <code>.exe</code> installer wizard with Desktop shortcuts.
          </p>
          <span className="text-xs font-medium text-brand-600 flex items-center gap-1">
            <span>Read Guide</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </span>
        </Link>

        <Link
          href="/docs/installation/macos"
          className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-brand-500 transition-colors space-y-3"
        >
          <Apple className="w-6 h-6 text-slate-700 dark:text-slate-300" />
          <h3 className="font-bold text-slate-900 dark:text-white">macOS</h3>
          <p className="text-xs text-slate-500">
            Running via Python 3.10+ virtualenv or pip install.
          </p>
          <span className="text-xs font-medium text-brand-600 flex items-center gap-1">
            <span>Read Guide</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </span>
        </Link>
      </div>
    </div>
  );
}
