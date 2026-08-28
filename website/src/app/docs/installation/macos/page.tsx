import { CommandBlock } from "@/components/CommandBlock";

export const metadata = {
  title: "macOS Installation Guide | Photo Face Organizer Docs",
  description: "Complete setup guide for macOS Apple Silicon and Intel systems.",
};

export default function MacOSInstallationPage() {
  return (
    <div className="space-y-8 text-slate-700 dark:text-slate-300">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-6 space-y-2">
        <span className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
          Installation &rsaquo; macOS
        </span>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
          macOS Installation Guide
        </h1>
        <p className="text-sm text-slate-500">
          Setup guide for macOS (Apple Silicon M1/M2/M3 &amp; Intel Macs).
        </p>
      </div>

      <div className="space-y-6 text-sm leading-relaxed">
        <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900 text-amber-800 dark:text-amber-200 text-xs">
          <strong>macOS Status Note:</strong> Standalone macOS <code>.dmg</code> build pipeline is currently in development. macOS users can install and run the full desktop application via Python pip/pipx.
        </div>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          Installing via Command Line (Pip / Pipx)
        </h2>

        <p className="font-semibold text-slate-900 dark:text-white">1. Ensure Python 3.10+ is installed:</p>
        <CommandBlock command="python3 --version" language="bash" />

        <p className="font-semibold text-slate-900 dark:text-white">2. Install Photo Face Organizer:</p>
        <CommandBlock
          command="pip install git+https://github.com/technoharsh21/photo-face-organizer.git"
          language="bash"
        />

        <p className="font-semibold text-slate-900 dark:text-white">3. Launch Application:</p>
        <CommandBlock command="photo-face-organizer" language="bash" />

        <h2 className="text-xl font-bold text-slate-900 dark:text-white pt-4">
          Gatekeeper &amp; Security Permissions
        </h2>
        <p className="text-xs text-slate-600 dark:text-slate-400">
          Ensure macOS Terminal or Python has read access to your Photos or target image directories under <strong>System Settings &rsaquo; Privacy &amp; Security &rsaquo; Full Disk Access</strong> if prompted.
        </p>
      </div>
    </div>
  );
}
