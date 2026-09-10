import Link from "next/link";

export const metadata = {
  title: "Results, Audit & Corrections | Photo Face Organizer Docs",
  description: "Verify the file reconciliation audit, inspect output folders, export the skipped-file log, correct wrong matches, and use safe Move mode.",
};

export default function ResultsAuditDocPage() {
  return (
    <div className="space-y-8 text-slate-700 dark:text-slate-300">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-6 space-y-2">
        <span className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
          Usage Guide &rsaquo; After the Scan
        </span>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
          Results, Audit &amp; Corrections
        </h1>
        <p className="text-sm text-slate-500">
          How Photo Face Organizer proves that no photo went missing, and how to fix a misfiled one.
        </p>
      </div>

      <div className="space-y-6 text-sm leading-relaxed">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          1. The File Reconciliation Audit
        </h2>
        <p>
          When a scan finishes, the Results page opens with a one-line audit instead of a bare &ldquo;done&rdquo;. It adds every discovered photo up across three buckets &mdash; matched, no-match, and skipped &mdash; and compares the total against the number of files discovered on disk:
        </p>
        <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs space-y-1">
          <p className="font-mono text-emerald-600 dark:text-emerald-400">File Reconciliation Audit: Accounted: 4,182 / 4,182 (100%) &bull; &#128994; Zero Photos Lost</p>
          <p className="font-mono text-amber-600 dark:text-amber-400">File Reconciliation Audit: Accounted: 4,179 / 4,182 (99.93%) &bull; &#9888;&#65039; 3 Missed Photos</p>
        </div>
        <p>
          A clean run reconciles to 100%. Anything less is flagged explicitly with the missed count rather than being silently rounded away, so a gap is impossible to miss. Alongside it sit the run&apos;s headline counters: <strong>processed</strong>, <strong>matched</strong>, <strong>no match</strong>, <strong>unknown faces</strong> captured, and <strong>duration</strong>.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          2. Inspecting Output Folders
        </h2>
        <p>
          The page is a split view: <em>&ldquo;Person Output Folders &amp; Matched Photos&rdquo;</em> on the left as a tree of destination folders and their files, and <em>&ldquo;Photo Preview &amp; Match Details&rdquo;</em> on the right. Selecting a folder shows its path and photo count; selecting a file previews it with its match details, and <Link href="/docs/photo-viewer">&#128269; the lightbox</Link> opens it full-size.
        </p>
        <p>
          <strong>&#128194; Open Output Folder</strong> hands off to your file manager at the destination root, so you can browse the organized albums natively.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          3. Skipped &amp; Error Files, Exportable
        </h2>
        <p>
          <strong>&#8505;&#65039; Skipped Details</strong> opens <em>&ldquo;Skipped &amp; Error File Details&rdquo;</em>, which lists the exact files that were not processed and why &mdash; a corrupt or unsupported image, an unreadable RAW, a file that vanished mid-scan &mdash; together with their resolution status.
        </p>
        <p>
          Both buttons at the bottom export the full list for record-keeping: <strong>&#128229; Export Audit Log (.txt)</strong> for reading and <strong>&#128229; Export Audit Log (.json)</strong> for scripting. This is the file to attach when reporting a &ldquo;why wasn&apos;t this photo sorted?&rdquo; bug.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          4. Correcting a Wrong Match
        </h2>
        <p>
          No recognition engine is perfect, so corrections are part of the workflow rather than a manual file-shuffle afterwards. Select a misfiled photo and click <strong>&#128295;&#65039; Correct Match</strong> to open the <em>&ldquo;Correct Photo Match&rdquo;</em> dialog, reassign the photo, and confirm with <strong>Apply Correction</strong>.
        </p>
        <p>
          If the photo actually contains several people and the app cannot tell which face drove the routing, a <em>&ldquo;&#128100; Select the Correct Person&apos;s Face&rdquo;</em> picker shows the detected faces so you can point at the right one and press <strong>Use Selected Face</strong>. Corrections also feed back into the profile, which tightens future scans. See <Link href="/docs/quality-ratings">&#129529; Clean Outliers</Link> for the bulk version of the same idea.
        </p>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          5. Copy Mode vs Move Mode
        </h2>
        <p>
          <strong>Step 3 of the New Scan Wizard</strong> chooses the file-handling mode. <strong>Copy Mode (Safe)</strong> is the default and never touches your originals. <strong>Move Mode</strong> does relocate photos, but only through a verification gate:
        </p>
        <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-2 text-xs">
          <p>&bull; <strong>Stage 1:</strong> every photo is copied to the output directory as normal.</p>
          <p>&bull; <strong>Stage 2:</strong> each copy is re-read and verified on disk before anything is removed.</p>
          <p>&bull; <strong>Stage 3:</strong> only if the run verifies completely does the app ask &mdash; in a dialog whose default button is <em>No</em> &mdash; whether to delete the originals.</p>
          <p>&bull; <strong>If verification is incomplete:</strong> a warning states that source files have <strong>not</strong> been deleted. Nothing is removed for a partial match.</p>
        </div>
        <p>
          Deleting originals is never automatic, never the default answer, and happens only after the copies are proven present and readable.
        </p>

        <div className="p-4 rounded-xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900 text-blue-800 dark:text-blue-200 text-sm">
          &#128161; <strong>Deleting a history record does not delete photos.</strong> History and Results records are metadata only &mdash; your organized output files are never touched by clearing them.
        </div>
      </div>
    </div>
  );
}
