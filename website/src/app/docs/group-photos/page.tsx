export const metadata = {
  title: "Group Photos & Compulsory Profiles | Photo Face Organizer Docs",
  description: "Learn how compulsory group photo matching works in Photo Face Organizer.",
};

export default function GroupPhotosDocPage() {
  return (
    <div className="space-y-8 text-slate-700 dark:text-slate-300">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-6 space-y-2">
        <span className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
          Usage Guide &rsaquo; Group Photos
        </span>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
          Group Photos &amp; Compulsory Group Profiles
        </h1>
        <p className="text-sm text-slate-500">
          How multi-person photos are evaluated and routed to multiple output folders.
        </p>
      </div>

      <div className="space-y-6 text-sm leading-relaxed">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">1. Multi-Person Photo Routing</h2>
        <p>
          If a single scanned photo contains multiple recognized faces (e.g. Alice and Bob), the application copies that photo to:
        </p>
        <ul className="list-disc list-inside space-y-1 font-mono text-xs text-brand-600 dark:text-brand-400">
          <li>Output/Alice/photo.jpg</li>
          <li>Output/Bob/photo.jpg</li>
          <li>Output/Alice &amp; Bob/photo.jpg (if a Group Profile exists)</li>
        </ul>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white pt-4">2. Compulsory Matching Rules</h2>
        <p>
          A **Group Profile** (e.g., &quot;Me &amp; Partner&quot;) enforces a strict compulsory requirement:
        </p>

        <div className="p-4 rounded-xl bg-purple-50 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-900 text-purple-900 dark:text-purple-200 text-xs leading-relaxed space-y-2">
          <p><strong>Rule:</strong> ALL compulsory member profiles (or all reference faces inside the Group Profile) MUST be detected together in a single photo before the photo is copied into the Group Profile folder.</p>
          <p>• Photo with Alice ONLY &rarr; Copies to <code>Output/Alice/</code> only.</p>
          <p>• Photo with Bob ONLY &rarr; Copies to <code>Output/Bob/</code> only.</p>
          <p>• Photo with Alice AND Bob &rarr; Copies to <code>Output/Alice/</code>, <code>Output/Bob/</code>, AND <code>Output/Alice &amp; Bob/</code>!</p>
        </div>
      </div>
    </div>
  );
}
