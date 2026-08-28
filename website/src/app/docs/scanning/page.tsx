export const metadata = {
  title: "Scanning & Matching Rules | Photo Face Organizer Docs",
  description: "Learn how to select folders, configure recursive scanning, and set matching thresholds.",
};

export default function ScanningDocPage() {
  return (
    <div className="space-y-8 text-slate-700 dark:text-slate-300">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-6 space-y-2">
        <span className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
          Usage Guide &rsaquo; Scanning
        </span>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
          Scanning &amp; Matching Thresholds
        </h1>
        <p className="text-sm text-slate-500">
          Folder discovery, recursive scanning, and facial matching calibration.
        </p>
      </div>

      <div className="space-y-6 text-sm leading-relaxed">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">1. Selecting Source Folders &amp; Files</h2>
        <p>
          In the <strong>New Scan Wizard (Step 1)</strong>, click <strong>📂 Add Folders</strong> to select one or multiple image directories. Check <strong>Include Subdirectories (Recursive)</strong> to analyze nested folders.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">2. Selecting Profiles for the Scan</h2>
        <p>
          In <strong>Step 2</strong>, select which individual and group profiles to include in the scan. Only selected profiles will be evaluated during the routing phase.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">3. Face Distance Calibration &amp; Thresholds</h2>
        <p>
          The engine computes facial vector distance ($d$). A smaller distance means higher similarity:
        </p>

        <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 font-mono text-xs space-y-1">
          <p>• Distance &le; 0.60 &rarr; Match Score 50.0% to 100.0% (Default Match)</p>
          <p>• Distance &gt; 0.60 &rarr; No Match (Sent to No Match folder &amp; Unknown Faces)</p>
        </div>
      </div>
    </div>
  );
}
