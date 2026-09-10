import Link from "next/link";

export const metadata = {
  title: "Scan History & Crash Recovery | Photo Face Organizer Docs",
  description: "Resume interrupted or cancelled scans, review past run statistics, and manage history records without touching organized photos.",
};

export default function HistoryDocPage() {
  return (
    <div className="space-y-8 text-slate-700 dark:text-slate-300">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-6 space-y-2">
        <span className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
          Usage Guide &rsaquo; Recovery
        </span>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
          Scan History &amp; Crash Recovery
        </h1>
        <p className="text-sm text-slate-500">
          Large libraries take a long time to process. Here is how an interrupted run gets finished instead of restarted.
        </p>
      </div>

      <div className="space-y-6 text-sm leading-relaxed">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          1. Resuming an Interrupted Scan
        </h2>
        <p>
          Every scan&apos;s progress is persisted as it runs. If the app is closed mid-scan, crashes, or loses power, the next launch detects the unfinished run and opens the <em>&ldquo;Interrupted Scan Detected&rdquo;</em> dialog (<strong>&#9888;&#65039; Previous Scan Interrupted</strong>) with three choices:
        </p>
        <ul className="list-disc list-inside space-y-1.5 pl-2 text-slate-600 dark:text-slate-400">
          <li><strong>Resume Scan</strong> &mdash; continue from where it stopped, skipping photos already processed. This is the option a 40,000-photo library needs.</li>
          <li><strong>Restart</strong> &mdash; take you to the New Scan Wizard to reconfigure from scratch.</li>
          <li><strong>Discard Recovery</strong> &mdash; abandon that run. Photos already copied stay exactly where they are; nothing is rolled back or deleted.</li>
        </ul>
        <p>
          The same resume path is available later from the History table, so a run you cancelled yesterday can be picked up today.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          2. The History Ledger
        </h2>
        <p>
          <strong>&#128203; History</strong> (<em>&ldquo;Scan History &amp; Run Logs&rdquo;</em>) is a full audit log of every run, with a summary bar above the table showing <strong>&#128202; Total Scans</strong>, <strong>&#128994; Completed</strong>, and <strong>&#128248; Photos Processed</strong> across all of them.
        </p>
        <p>Each row records:</p>
        <ul className="list-disc list-inside space-y-1.5 pl-2 text-slate-600 dark:text-slate-400">
          <li><strong>Date / Time</strong> the run started</li>
          <li><strong>Status</strong> &mdash; colour-coded: &#128994; Completed, &#128993; Paused / Interrupted, &#128308; Cancelled / Failed, &#9889; anything still active</li>
          <li><strong>Total Files</strong>, <strong>Matched</strong>, and <strong>No Match</strong> counts</li>
          <li><strong>Duration</strong> in seconds</li>
        </ul>
        <p>
          The <strong>&#128269; Filter scan history records by date or status</strong> box narrows the table live as you type, matching against any of those columns.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          3. Row Actions
        </h2>
        <ul className="list-disc list-inside space-y-1.5 pl-2 text-slate-600 dark:text-slate-400">
          <li><strong>&#127919; View Results</strong> &mdash; reload that run&apos;s Results page, including its reconciliation audit and output tree, long after the scan finished.</li>
          <li><strong>&#9654; Resume</strong> &mdash; appears on rows that are Paused, Interrupted, or Running, and restarts processing from the saved position.</li>
          <li><strong>&#128465; Delete</strong> &mdash; removes that single metadata record.</li>
        </ul>
        <p>
          <strong>&#128465; Clear All History</strong> empties the ledger. Both deletions confirm first, and both confirmations state the guarantee explicitly: <em>&ldquo;Output files in your folders will NEVER be touched.&rdquo;</em> History is bookkeeping, not the location of your photos.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          4. What Is Stored, and Where
        </h2>
        <p>
          History is an append-only local record (a JSONL file) in the application data directory alongside profiles, encodings, and the face cache &mdash; see <Link href="/docs/privacy-data">Privacy &amp; File Safety</Link> for the per-platform paths. It is plain, human-readable text on your own disk, and clearing it has no effect on your photo library.
        </p>

        <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-400">
          &#128274; <strong>Why the tabs go grey during a scan.</strong> While a scan is active, sidebar navigation is locked (with a tooltip explaining why) so folder sets and profiles cannot change underneath a running job. The Processing and Results pages stay reachable, and the lock releases the moment the run finishes, is cancelled, or is paused.
        </div>
      </div>
    </div>
  );
}
