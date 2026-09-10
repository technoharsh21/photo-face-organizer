import Link from "next/link";

export const metadata = {
  title: "Settings & Face Cache | Photo Face Organizer Docs",
  description: "Performance profiles, GPU device preference, the matching precision threshold scale, and the SQLite face-embedding cache that makes rescans near-instant.",
};

export default function SettingsDocPage() {
  return (
    <div className="space-y-8 text-slate-700 dark:text-slate-300">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-6 space-y-2">
        <span className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
          Configuration &rsaquo; Settings
        </span>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
          Settings &amp; Face Cache
        </h1>
        <p className="text-sm text-slate-500">
          Everything you can tune: which hardware runs inference, how strict matching is, and how much work gets remembered between runs.
        </p>
      </div>

      <div className="space-y-6 text-sm leading-relaxed">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          1. Hardware Status Banner
        </h2>
        <p>
          The card at the top reports what the engine actually bound to at startup &mdash; for example <em>&ldquo;&#128994; Active AI Hardware: NVIDIA CUDA GPU (GPU Accelerated)&rdquo;</em> &mdash; plus the loaded model, <strong>InsightFace (SCRFD 360&deg; + ArcFace 512-d)</strong>. This is the fastest way to confirm acceleration is live rather than silently falling back to CPU. (Provider details: <Link href="/docs/hardware">Hardware &amp; Acceleration</Link>.)
        </p>
        <p>
          <strong>&#128203; View Diagnostic Logs</strong> opens <em>&ldquo;Hardware Acceleration &amp; Diagnostic Logs&rdquo;</em>, which shows the local <code>photo_face_organizer.log</code> with <strong>&#128203; Copy Logs to Clipboard</strong> and <strong>&#128194; Open Log File</strong>. Attach that log to bug reports &mdash; it records provider selection and every inference fallback.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          2. Performance Profile &amp; Device Preference
        </h2>
        <p>Two independent controls:</p>
        <ul className="list-disc list-inside space-y-1.5 pl-2 text-slate-600 dark:text-slate-400">
          <li><strong>Performance Profile</strong> &mdash; <em>Maximum Performance</em> (default), <em>Balanced</em>, or <em>Eco</em>. Controls how aggressively the concurrent worker pipeline saturates the machine; Eco is the one to pick if you need the laptop usable, quiet, or cool while a 30,000-photo scan runs overnight.</li>
          <li><strong>AI Hardware Preference</strong> &mdash; <em>Auto (GPU Priority - Recommended)</em>, <em>DirectX 12 GPU (DirectML)</em>, <em>NVIDIA CUDA GPU</em>, or <em>Multi-Core CPU</em>. Auto tries the best available accelerator and falls back gracefully; the explicit options exist for when you want to force a device to prove a speed difference or route around a flaky driver.</li>
        </ul>
        <p>
          These same two choices also appear in Step 4 of the New Scan Wizard, so a single scan can deviate from your global defaults without changing them.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          3. Default Matching Precision Threshold
        </h2>
        <p>
          A slider (with a numeric box) from <strong>1% to 100%</strong>, defaulting to <strong>50%</strong>. It sets the minimum calibrated similarity score for a face to count as a profile match in ordinary scans, and its label updates live to explain the trade-off you are choosing:
        </p>
        <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
          <table className="w-full text-xs">
            <thead className="bg-slate-100 dark:bg-slate-900 text-slate-700 dark:text-slate-300">
              <tr>
                <th className="px-4 py-2 text-left font-semibold">Range</th>
                <th className="px-4 py-2 text-left font-semibold">Behaviour</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-slate-600 dark:text-slate-400">
              <tr><td className="px-4 py-2 font-semibold">&#128274; 85&ndash;100%</td><td className="px-4 py-2">Ultra-Strict Precision &mdash; near-identical matches only, zero false positives.</td></tr>
              <tr><td className="px-4 py-2 font-semibold">&#127919; 70&ndash;84%</td><td className="px-4 py-2">High Precision &mdash; recommended for Solo scans.</td></tr>
              <tr><td className="px-4 py-2 font-semibold">&#9878;&#65039; 50&ndash;69%</td><td className="px-4 py-2">Balanced (default) &mdash; tolerates hairstyle, expression, and lighting changes.</td></tr>
              <tr><td className="px-4 py-2 font-semibold">&#128461; 35&ndash;49%</td><td className="px-4 py-2">Extended Range &mdash; catches side profiles and photos taken with sunglasses or hats.</td></tr>
              <tr><td className="px-4 py-2 font-semibold">&#128269; 1&ndash;34%</td><td className="px-4 py-2">Maximum Sensitivity &mdash; loose matching for low-resolution or dark nighttime photos.</td></tr>
            </tbody>
          </table>
        </div>
        <p>
          Lower values find more photos of the right person <em>and</em> more photos of people who merely resemble them; higher values do the reverse. If a profile is collecting strangers, raise the threshold rather than deleting results by hand.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          4. Face Processing Disk Cache
        </h2>
        <p>
          <strong>&ldquo;Enable Face Processing Disk Cache (1,000x Faster Rescans)&rdquo;</strong> is on by default. When enabled, the detected face locations and 512-d embeddings for each photo are written to a local SQLite cache keyed by the file&apos;s SHA-256 content hash, so a repeat scan of the same library reads numbers from disk instead of re-running the neural network &mdash; roughly <strong>0.0005&nbsp;s per photo</strong>.
        </p>
        <p>
          Because the key is a content hash, editing or replacing a photo changes its key and the photo is simply re-processed; a stale entry cannot poison a result. <strong>&#129529; Clear Cache</strong> confirms first, then reports how many cached entries it removed and how many megabytes you got back. The cache holds derived data only &mdash; clearing it never touches your photos or profiles.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          5. Storage Directory &amp; Saving
        </h2>
        <p>
          The <strong>&#128193; Local Application Storage Directory</strong> card shows the exact path holding your profiles, encodings, checkpoints, cache, and history, with <strong>&#128194; Open Folder</strong> to reveal it in your file manager.
        </p>
        <p>
          <strong>&#128190; Save Settings</strong> persists your choices and re-binds the engine to the selected device immediately. <strong>&#128283; Reset Defaults</strong> restores Maximum Performance, Auto device priority, 50% threshold, and cache enabled.
        </p>

        <div className="p-4 rounded-xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900 text-blue-800 dark:text-blue-200 text-sm">
          &#128274; The cache and logs live inside the same local application directory as your profiles. Nothing in Settings turns on telemetry or cloud sync &mdash; there is no remote endpoint to point any of it at.
        </div>
      </div>
    </div>
  );
}
